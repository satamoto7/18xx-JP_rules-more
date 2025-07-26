#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
画像最適化機能付きゲーム追加スクリプト
"""

import yaml
import os
import sys
import argparse
import re
import platform
import subprocess
from pathlib import Path
from datetime import datetime

class ImageOptimizer:
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.images_dir = self.project_root / "docs" / "assets" / "images"
        self.backup_dir = self.images_dir / "backup"
        self.is_windows = platform.system() == "Windows"
        
        # 最適化設定
        self.settings = {
            'width': 400,
            'height': 600,
            'quality': 85,
            'max_file_size': 200 * 1024,  # 200KB
            'preserve_original': True,
            'auto_optimize': True
        }
        
    def ensure_imagemagick(self):
        """ImageMagickがインストールされているかチェック"""
        try:
            result = subprocess.run(['magick', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def print_safe(self, text):
        """Windows環境での安全な出力"""
        try:
            print(text)
        except UnicodeEncodeError:
            safe_text = text.replace('🖼️', '[IMG]').replace('✅', '[OK]').replace('❌', '[ERROR]')
            print(safe_text)
    
    def get_image_info(self, image_path):
        """画像の詳細情報を取得"""
        try:
            cmd = ['magick', 'identify', '-format', '%w %h %b', str(image_path)]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                parts = result.stdout.strip().split()
                return {
                    'width': int(parts[0]),
                    'height': int(parts[1]),
                    'file_size_str': parts[2],
                    'file_size': os.path.getsize(image_path)
                }
        except (subprocess.TimeoutExpired, ValueError, IndexError):
            pass
        
        # フォールバック: ファイルサイズのみ
        return {
            'width': 0,
            'height': 0,
            'file_size_str': 'unknown',
            'file_size': os.path.getsize(image_path)
        }
    
    def needs_optimization(self, image_path):
        """最適化が必要かどうか判定"""
        if not os.path.exists(image_path):
            return False
            
        info = self.get_image_info(image_path)
        
        # ファイルサイズチェック
        if info['file_size'] > self.settings['max_file_size']:
            return True
            
        # 解像度チェック（ImageMagickが利用可能な場合）
        if info['width'] > 0 and info['height'] > 0:
            if (info['width'] > self.settings['width'] * 1.2 or 
                info['height'] > self.settings['height'] * 1.2):
                return True
                
        return False
    
    def create_backup(self, image_path):
        """バックアップファイルを作成"""
        if not self.settings['preserve_original']:
            return True
            
        try:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            backup_path = self.backup_dir / Path(image_path).name
            
            if not backup_path.exists():
                import shutil
                shutil.copy2(image_path, backup_path)
                self.print_safe(f"📁 バックアップ作成: {backup_path.name}")
            
            return True
        except Exception as e:
            self.print_safe(f"❌ バックアップ作成エラー: {e}")
            return False
    
    def optimize_image(self, image_path):
        """画像を最適化"""
        if not self.ensure_imagemagick():
            self.print_safe("❌ ImageMagickが見つかりません。最適化をスキップします。")
            return False
        
        if not os.path.exists(image_path):
            self.print_safe(f"❌ ファイルが見つかりません: {image_path}")
            return False
        
        # 最適化が必要かチェック
        if not self.needs_optimization(image_path):
            self.print_safe(f"✅ 最適化不要: {Path(image_path).name}")
            return True
        
        original_info = self.get_image_info(image_path)
        self.print_safe(f"🖼️ 最適化中: {Path(image_path).name}")
        self.print_safe(f"   元サイズ: {original_info['width']}x{original_info['height']}, "
                       f"{original_info['file_size'] // 1024}KB")
        
        # バックアップ作成
        if not self.create_backup(image_path):
            return False
        
        # 一時ファイル作成
        temp_path = str(image_path) + '.temp'
        
        try:
            # ImageMagickコマンド実行
            cmd = [
                'magick', str(image_path),
                '-auto-orient',
                '-strip',
                '-resize', f"{self.settings['width']}x{self.settings['height']}>",
                '-quality', str(self.settings['quality']),
                temp_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and os.path.exists(temp_path):
                # 最適化されたファイルで置き換え
                os.replace(temp_path, image_path)
                
                # 結果表示
                new_info = self.get_image_info(image_path)
                reduction = ((original_info['file_size'] - new_info['file_size']) / 
                           original_info['file_size'] * 100)
                
                self.print_safe(f"   最適化後: {new_info['width']}x{new_info['height']}, "
                               f"{new_info['file_size'] // 1024}KB")
                self.print_safe(f"   削減率: {reduction:.1f}%")
                
                return True
            else:
                self.print_safe(f"❌ 最適化失敗: {result.stderr}")
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                return False
                
        except Exception as e:
            self.print_safe(f"❌ 最適化エラー: {e}")
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return False
    
    def optimize_all_images(self):
        """すべての画像を最適化"""
        if not self.images_dir.exists():
            self.print_safe("❌ 画像ディレクトリが見つかりません")
            return False
        
        image_extensions = ('.jpg', '.jpeg', '.png')
        image_files = []
        
        for ext in image_extensions:
            image_files.extend(self.images_dir.glob(f"*{ext}"))
            image_files.extend(self.images_dir.glob(f"*{ext.upper()}"))
        
        # バックアップディレクトリの画像は除外
        image_files = [f for f in image_files if 'backup' not in str(f)]
        
        if not image_files:
            self.print_safe("📝 最適化対象の画像ファイルがありません")
            return True
        
        self.print_safe(f"🖼️ {len(image_files)}個の画像ファイルをチェック中...")
        
        optimized_count = 0
        total_savings = 0
        
        for image_file in image_files:
            if self.needs_optimization(image_file):
                original_size = os.path.getsize(image_file)
                
                if self.optimize_image(image_file):
                    new_size = os.path.getsize(image_file)
                    total_savings += (original_size - new_size)
                    optimized_count += 1
        
        # サマリー表示
        if optimized_count > 0:
            self.print_safe(f"\n✅ 最適化完了:")
            self.print_safe(f"   処理ファイル数: {optimized_count}")
            self.print_safe(f"   削減サイズ: {total_savings // 1024}KB")
        else:
            self.print_safe("✅ すべての画像が既に最適化されています")
        
        return True
    
    def check_image_requirements(self, image_path):
        """画像がサイト要件を満たしているかチェック"""
        if not os.path.exists(image_path):
            return False, "ファイルが存在しません"
        
        info = self.get_image_info(image_path)
        issues = []
        
        # ファイルサイズチェック
        if info['file_size'] > self.settings['max_file_size']:
            issues.append(f"ファイルサイズが大きすぎます ({info['file_size'] // 1024}KB)")
        
        # アスペクト比チェック（ImageMagickが利用可能な場合）
        if info['width'] > 0 and info['height'] > 0:
            aspect_ratio = info['width'] / info['height']
            target_ratio = self.settings['width'] / self.settings['height']  # 3:4 = 0.75
            
            if abs(aspect_ratio - target_ratio) > 0.1:  # 10%以上の差
                issues.append(f"アスペクト比が推奨値と異なります ({aspect_ratio:.2f}, 推奨: {target_ratio:.2f})")
        
        return len(issues) == 0, "; ".join(issues)

# ゲーム追加スクリプトとの統合
class EnhancedGameAdder:
    def __init__(self):
        self.script_dir = Path(__file__).parent  # scripts フォルダ
        self.docs_dir = self.script_dir.parent / "docs"  # docs フォルダ
        self.games_yml_path = self.docs_dir / "_data" / "games.yml"
        self.images_dir = self.docs_dir / "assets" / "images"
        self.downloads_dir = self.docs_dir / "downloads"
        self.is_windows = platform.system() == "Windows"
        
        # 画像最適化クラスを初期化
        self.image_optimizer = ImageOptimizer(self.docs_dir.parent)  # プロジェクトルート
    
    def print_safe(self, text):
        """Windows環境での安全な出力"""
        try:
            print(text)
        except UnicodeEncodeError:
            safe_text = text.replace('🎲', '[GAME]').replace('🖼️', '[IMG]').replace('✅', '[OK]').replace('❌', '[ERROR]')
            print(safe_text)
    
    def ensure_directories(self):
        """必要なディレクトリを作成"""
        dirs_to_create = [
            self.images_dir,
            self.downloads_dir / "rules",
            self.downloads_dir / "summaries"
        ]
        
        for dir_path in dirs_to_create:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def load_games_data(self):
        """既存のゲームデータを読み込み"""
        if self.games_yml_path.exists():
            try:
                with open(self.games_yml_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {'games': []}
            except Exception as e:
                self.print_safe(f"❌ ファイル読み込みエラー: {e}")
                return {'games': []}
        return {'games': []}
    
    def save_games_data(self, data):
        """ゲームデータを保存"""
        try:
            # バックアップ作成
            if self.games_yml_path.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = self.games_yml_path.with_suffix(f'.yml.backup.{timestamp}')
                import shutil
                shutil.copy2(str(self.games_yml_path), str(backup_path))
            
            with open(self.games_yml_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
            return True
        except Exception as e:
            self.print_safe(f"❌ ファイル保存エラー: {e}")
            return False
    
    def safe_input(self, prompt):
        """安全な入力"""
        try:
            return input(prompt).strip()
        except:
            self.print_safe("❌ 入力エラー")
            return ""
    
    def validate_and_optimize_image(self, image_filename):
        """画像ファイルの検証と最適化"""
        if not image_filename:
            return True  # 画像なしも許可
        
        image_path = self.images_dir / image_filename
        
        if not image_path.exists():
            self.print_safe(f"⚠️  画像ファイルが見つかりません: {image_path}")
            self.print_safe(f"    ファイルを {self.images_dir} に配置してください")
            return False
        
        # 画像要件チェック
        is_valid, message = self.image_optimizer.check_image_requirements(image_path)
        
        if not is_valid:
            self.print_safe(f"⚠️  画像の問題: {message}")
            
            # 自動最適化を提案
            if self.image_optimizer.settings['auto_optimize']:
                choice = self.safe_input("自動で最適化しますか？ (y/n): ").lower()
                if choice == 'y':
                    if self.image_optimizer.optimize_image(image_path):
                        self.print_safe("✅ 画像最適化完了")
                        return True
                    else:
                        self.print_safe("❌ 画像最適化失敗")
                        return False
                else:
                    return False
            else:
                return False
        else:
            self.print_safe("✅ 画像は要件を満たしています")
            return True
    
    def add_new_game_with_optimization(self):
        """画像最適化機能付きゲーム追加"""
        self.print_safe("🎲 新しいボードゲームを追加します（画像最適化機能付き）\n")
        
        game_data = {}
        
        # 基本情報入力
        game_data['title'] = self.safe_input("ゲーム名: ")
        if not game_data['title']:
            self.print_safe("❌ ゲーム名は必須です")
            return None
        
        # ID生成
        suggested_id = re.sub(r'[^a-z0-9-]', '', game_data['title'].lower().replace(' ', '-').replace('　', '-'))
        if not suggested_id:
            suggested_id = "new-game"
        
        game_id = self.safe_input(f"ID [{suggested_id}]: ") or suggested_id
        
        # 重複チェック
        existing_data = self.load_games_data()
        existing_ids = [game.get('id') for game in existing_data.get('games', [])]
        if game_id in existing_ids:
            self.print_safe(f"❌ ID '{game_id}' は既に使用されています")
            return None
        
        game_data['id'] = game_id
        game_data['players'] = self.safe_input("プレイ人数 (例: 2-4人): ")
        game_data['time'] = self.safe_input("プレイ時間 (例: 30-60分): ")
        game_data['age'] = self.safe_input("対象年齢 (例: 10歳以上): ")
        
        # 難易度選択
        difficulty_map = {
            '1': ('beginner', '初心者向け'),
            '2': ('intermediate', '経験者向け'),
            '3': ('expert', 'エキスパート向け')
        }
        
        self.print_safe("\n難易度を選択:")
        for key, (_, text) in difficulty_map.items():
            self.print_safe(f"  {key}: {text}")
        
        while True:
            choice = self.safe_input("選択 (1-3): ")
            if choice in difficulty_map:
                game_data['difficulty'] = difficulty_map[choice][0]
                game_data['difficultyText'] = difficulty_map[choice][1]
                break
            self.print_safe("❌ 1-3で選択してください")
        
        game_data['description'] = self.safe_input("ゲームの説明: ")
        
        # 画像ファイル設定と最適化
        self.print_safe(f"\n🖼️ 画像設定")
        suggested_image = f"{game_id}.jpg"
        image_filename = self.safe_input(f"画像ファイル名 [{suggested_image}]: ") or suggested_image
        
        if image_filename:
            # 画像の検証と最適化
            if self.validate_and_optimize_image(image_filename):
                game_data['image'] = image_filename
            else:
                self.print_safe("❌ 画像の設定に問題があります")
                continue_choice = self.safe_input("画像なしで続行しますか？ (y/n): ").lower()
                if continue_choice != 'y':
                    return None
        
        # PDF設定
        suggested_rules = f"/downloads/rules/{game_id}-rules.pdf"
        suggested_summary = f"/downloads/summaries/{game_id}-summary.pdf"
        
        game_data['rulesUrl'] = self.safe_input(f"ルール和訳PDFパス [{suggested_rules}]: ") or suggested_rules
        game_data['summaryUrl'] = self.safe_input(f"サマリーシートPDFパス [{suggested_summary}]: ") or suggested_summary
        
        return game_data
    
    def preview_with_image_status(self, game_data):
        """画像状態を含むプレビュー"""
        self.print_safe("\n" + "="*50)
        self.print_safe("📋 追加予定のゲーム情報:")
        self.print_safe("="*50)
        
        for key, value in game_data.items():
            self.print_safe(f"{key:15}: {value}")
        
        self.print_safe("="*50)
        
        # 画像状態チェック
        if game_data.get('image'):
            image_path = self.images_dir / game_data['image']
            if image_path.exists():
                info = self.image_optimizer.get_image_info(image_path)
                is_optimal = not self.image_optimizer.needs_optimization(image_path)
                status = "✅ 最適" if is_optimal else "⚠️  要最適化"
                
                self.print_safe(f"\n🖼️ 画像情報:")
                self.print_safe(f"   ファイル: {game_data['image']}")
                self.print_safe(f"   サイズ: {info['width']}x{info['height']} ({info['file_size'] // 1024}KB)")
                self.print_safe(f"   状態: {status}")
            else:
                self.print_safe(f"\n❌ 画像ファイル未配置: {game_data['image']}")
    
    def run_with_image_optimization(self):
        """画像最適化機能付きメイン処理"""
        try:
            self.ensure_directories()
            
            # ImageMagick確認
            if self.image_optimizer.ensure_imagemagick():
                self.print_safe("✅ ImageMagick利用可能")
            else:
                self.print_safe("⚠️  ImageMagick未検出 - 最適化機能は制限されます")
                self.print_safe("   インストールURL: https://imagemagick.org/script/download.php#windows")
            
            # ゲーム情報入力
            new_game = self.add_new_game_with_optimization()
            if not new_game:
                return False
            
            # プレビュー表示
            self.preview_with_image_status(new_game)
            
            # 確認
            confirm = self.safe_input("\n追加しますか？ (y/n): ").lower()
            if confirm != 'y':
                self.print_safe("❌ キャンセルしました")
                return False
            
            # データ保存
            data = self.load_games_data()
            data['games'].append(new_game)
            
            if self.save_games_data(data):
                self.print_safe(f"\n✅ '{new_game['title']}' を追加しました！")
                self.show_next_steps(new_game)
                
                # 全画像の最適化チェック
                optimize_all = self.safe_input("\nすべての画像を最適化チェックしますか？ (y/n): ").lower()
                if optimize_all == 'y':
                    self.image_optimizer.optimize_all_images()
                
                return True
            else:
                self.print_safe("❌ データ保存に失敗しました")
                return False
                
        except KeyboardInterrupt:
            self.print_safe("\n❌ 処理を中断しました")
            return False
        except Exception as e:
            self.print_safe(f"❌ エラーが発生しました: {e}")
            return False
    
    def show_next_steps(self, game_data):
        """次のステップを表示"""
        self.print_safe("\n📝 次のステップ:")
        
        steps = []
        step_num = 1
        
        # ファイル配置確認
        if game_data.get('image'):
            image_path = self.images_dir / game_data['image']
            if not image_path.exists():
                steps.append(f"{step_num}. 画像ファイル '{game_data['image']}' を docs/assets/images/ に配置")
                step_num += 1
        
        if game_data.get('rulesUrl'):
            file_path = game_data['rulesUrl'].replace('/', os.sep)
            full_path = self.docs_dir / file_path[1:]
            if not full_path.exists():
                steps.append(f"{step_num}. ルールPDF を docs{file_path} に配置")
                step_num += 1
        
        if game_data.get('summaryUrl'):
            file_path = game_data['summaryUrl'].replace('/', os.sep)
            full_path = self.docs_dir / file_path[1:]
            if not full_path.exists():
                steps.append(f"{step_num}. サマリーPDF を docs{file_path} に配置")
                step_num += 1
        
        # 共通ステップ
        steps.extend([
            f"{step_num}. git add, commit, push でサイトを更新",
            f"{step_num + 1}. ローカルで確認: bundle exec jekyll serve"
        ])
        
        for step in steps:
            self.print_safe(f"   {step}")

def main():
    parser = argparse.ArgumentParser(description='ボードゲームライブラリ管理ツール（画像最適化機能付き）')
    parser.add_argument('--add', action='store_true', help='新しいゲームを追加（デフォルト）')
    parser.add_argument('--optimize', action='store_true', help='すべての画像を最適化')
    parser.add_argument('--check', action='store_true', help='画像の最適化状況をチェック')
    
    args = parser.parse_args()
    
    # Windows環境での文字化け対策
    if platform.system() == "Windows":
        os.system('chcp 65001 >nul 2>&1')
    
    adder = EnhancedGameAdder()
    
    if args.optimize:
        # 画像最適化のみ実行
        adder.image_optimizer.optimize_all_images()
    elif args.check:
        # 画像チェックのみ実行
        images_dir = adder.images_dir
        if images_dir.exists():
            image_files = list(images_dir.glob("*.jpg")) + list(images_dir.glob("*.png"))
            image_files = [f for f in image_files if 'backup' not in str(f)]
            
            print(f"🖼️ 画像最適化状況チェック ({len(image_files)}ファイル)")
            print("-" * 60)
            
            for image_file in image_files:
                info = adder.image_optimizer.get_image_info(image_file)
                needs_opt = adder.image_optimizer.needs_optimization(image_file)
                status = "要最適化" if needs_opt else "最適"
                
                print(f"{image_file.name:20} {info['width']}x{info['height']:>8} {info['file_size']//1024:>4}KB {status}")
    else:
        # ゲーム追加（デフォルト）
        adder.run_with_image_optimization()

if __name__ == "__main__":
    main()