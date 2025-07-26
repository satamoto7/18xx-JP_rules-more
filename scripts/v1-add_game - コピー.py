#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ボードゲーム追加自動化スクリプト (Windows PowerShell対応版)
新しいゲームを対話形式で追加し、games.ymlを更新します

使用方法:
  python add_game.py            # 対話形式で追加
  python add_game.py --list     # 既存ゲーム一覧表示
  python add_game.py --validate # データ検証
"""

import yaml
import os
import sys
import argparse
import re
import platform
from pathlib import Path
from datetime import datetime

# Windows環境での文字化け対策
if platform.system() == "Windows":
    import locale
    try:
        # Windows のコンソールエンコーディングを UTF-8 に設定
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass

class GameAdder:
    def __init__(self):
        self.script_dir = Path(__file__).parent.parent  # docs/scripts/ から docs/ へ
        self.games_yml_path = self.script_dir / "_data" / "games.yml"
        self.images_dir = self.script_dir / "assets" / "images"
        self.downloads_dir = self.script_dir / "downloads"
        
        # Windows環境チェック
        self.is_windows = platform.system() == "Windows"
        
    def print_with_encoding(self, text):
        """Windows環境での安全な出力"""
        try:
            print(text)
        except UnicodeEncodeError:
            # 絵文字が表示できない場合は代替文字を使用
            safe_text = text.replace('🎲', '[GAME]').replace('📋', '[LIST]').replace('✅', '[OK]').replace('❌', '[ERROR]').replace('⚠️', '[WARN]').replace('📁', '[FOLDER]').replace('📝', '[NOTE]').replace('🔍', '[SEARCH]')
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
            if not dir_path.exists():
                self.print_with_encoding(f"📁 ディレクトリを作成しました: {dir_path}")
        
    def load_games_data(self):
        """既存のゲームデータを読み込み"""
        if self.games_yml_path.exists():
            try:
                with open(self.games_yml_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    return data or {'games': []}
            except Exception as e:
                self.print_with_encoding(f"❌ ファイル読み込みエラー: {e}")
                return {'games': []}
        return {'games': []}
    
    def save_games_data(self, data):
        """ゲームデータを保存（バックアップ付き）"""
        try:
            # バックアップ作成
            if self.games_yml_path.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = self.games_yml_path.with_suffix(f'.yml.backup.{timestamp}')
                
                # Windows環境での安全なファイルコピー
                import shutil
                shutil.copy2(str(self.games_yml_path), str(backup_path))
                self.print_with_encoding(f"📁 バックアップ作成: {backup_path.name}")
            
            # データ保存
            with open(self.games_yml_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
            self.print_with_encoding(f"✅ {self.games_yml_path} を更新しました")
            
        except Exception as e:
            self.print_with_encoding(f"❌ ファイル保存エラー: {e}")
            return False
        return True
    
    def validate_id(self, game_id):
        """IDの形式をチェック"""
        if not re.match(r'^[a-z0-9-]+$', game_id):
            return False, "IDは英小文字、数字、ハイフンのみ使用可能です"
        if game_id.startswith('-') or game_id.endswith('-'):
            return False, "IDの最初と最後にハイフンは使用できません"
        if len(game_id) < 2:
            return False, "IDは2文字以上で入力してください"
        return True, ""
    
    def safe_input(self, prompt):
        """Windows環境での安全な入力"""
        try:
            return input(prompt)
        except UnicodeDecodeError:
            # Windows環境でのエンコーディング問題対応
            import msvcrt
            self.print_with_encoding(prompt)
            return sys.stdin.readline().strip()
    
    def get_user_input(self, prompt, required=True, choices=None, validator=None):
        """ユーザー入力を取得（バリデーション付き）"""
        while True:
            try:
                value = self.safe_input(prompt).strip()
            except KeyboardInterrupt:
                raise
            except Exception:
                self.print_with_encoding("❌ 入力エラーが発生しました。もう一度入力してください。")
                continue
                
            if not required and not value:
                return None
            if value:
                if choices and value not in choices:
                    self.print_with_encoding(f"❌ {choices} から選択してください")
                    continue
                if validator:
                    is_valid, error_msg = validator(value)
                    if not is_valid:
                        self.print_with_encoding(f"❌ {error_msg}")
                        continue
                return value
            if required:
                self.print_with_encoding("❌ 必須項目です。入力してください。")
    
    def suggest_files(self, game_id):
        """ファイル名を提案"""
        suggestions = {
            'image': f"{game_id}.jpg",
            'rules': f"/downloads/rules/{game_id}-rules.pdf",
            'summary': f"/downloads/summaries/{game_id}-summary.pdf"
        }
        return suggestions
    
    def check_file_exists(self, file_path):
        """ファイルの存在をチェック"""
        try:
            if file_path.startswith('/downloads/'):
                full_path = self.downloads_dir / file_path[11:]  # "/downloads/" を除去
            elif file_path.endswith(('.jpg', '.png', '.jpeg')):
                full_path = self.images_dir / file_path
            else:
                return False
            return full_path.exists()
        except Exception:
            return False
    
    def list_games(self):
        """既存ゲーム一覧を表示"""
        data = self.load_games_data()
        games = data.get('games', [])
        
        if not games:
            self.print_with_encoding("📝 登録されているゲームはありません")
            return
        
        self.print_with_encoding(f"📚 登録済みゲーム一覧 ({len(games)}件)")
        self.print_with_encoding("-" * 60)
        for i, game in enumerate(games, 1):
            title = game.get('title', 'タイトル不明')
            game_id = game.get('id', 'ID不明')
            players = game.get('players', '?')
            time = game.get('time', '?')
            difficulty = game.get('difficultyText', '?')
            
            self.print_with_encoding(f"{i:2d}. {title} ({game_id})")
            self.print_with_encoding(f"     {players} | {time} | {difficulty}")
        self.print_with_encoding("-" * 60)
    
    def validate_data(self):
        """データの整合性をチェック"""
        data = self.load_games_data()
        games = data.get('games', [])
        
        self.print_with_encoding("🔍 データ検証を実行中...")
        errors = []
        warnings = []
        
        # 重複IDチェック
        ids = [game.get('id') for game in games if game.get('id')]
        duplicates = set([x for x in ids if ids.count(x) > 1])
        if duplicates:
            errors.append(f"重複ID: {', '.join(duplicates)}")
        
        # 各ゲームの検証
        for i, game in enumerate(games):
            game_id = game.get('id', f'game-{i}')
            
            # 必須フィールドチェック
            required_fields = ['id', 'title', 'players', 'time', 'age', 'difficulty', 'difficultyText', 'description']
            for field in required_fields:
                if not game.get(field):
                    errors.append(f"{game_id}: 必須フィールド '{field}' が未設定")
            
            # ファイル存在チェック
            if game.get('image'):
                if not self.check_file_exists(game['image']):
                    warnings.append(f"{game_id}: 画像ファイル '{game['image']}' が見つかりません")
            
            for url_field in ['rulesUrl', 'summaryUrl']:
                if game.get(url_field) and not self.check_file_exists(game[url_field]):
                    warnings.append(f"{game_id}: ファイル '{game[url_field]}' が見つかりません")
        
        # 結果表示
        if errors:
            self.print_with_encoding("❌ エラー:")
            for error in errors:
                self.print_with_encoding(f"   {error}")
        
        if warnings:
            self.print_with_encoding("⚠️  警告:")
            for warning in warnings:
                self.print_with_encoding(f"   {warning}")
        
        if not errors and not warnings:
            self.print_with_encoding("✅ データ検証完了 - 問題ありません")
        
        return len(errors) == 0
    
    def add_new_game(self):
        """新しいゲームを追加"""
        self.print_with_encoding("🎲 新しいボードゲームを追加します\n")
        
        # 基本情報の入力
        game_data = {}
        
        # ID（自動生成またはカスタム）
        title = self.get_user_input("ゲーム名: ")
        # Windows環境での安全な文字列処理
        suggested_id = re.sub(r'[^a-z0-9-]', '', title.lower().replace(' ', '-').replace('　', '-'))
        if not suggested_id:
            suggested_id = "new-game"
            
        game_id = self.get_user_input(
            f"ID [{suggested_id}]: ", 
            required=False, 
            validator=self.validate_id
        ) or suggested_id
        
        # 既存IDチェック
        existing_data = self.load_games_data()
        existing_ids = [game.get('id') for game in existing_data.get('games', [])]
        if game_id in existing_ids:
            self.print_with_encoding(f"❌ ID '{game_id}' は既に使用されています")
            game_id = self.get_user_input("別のIDを入力してください: ", validator=self.validate_id)
        
        game_data['id'] = game_id
        game_data['title'] = title
        
        # ファイル名提案
        suggestions = self.suggest_files(game_id)
        
        # その他の情報
        game_data['players'] = self.get_user_input("プレイ人数 (例: 2-4人): ")
        game_data['time'] = self.get_user_input("プレイ時間 (例: 30-60分): ")
        game_data['age'] = self.get_user_input("対象年齢 (例: 10歳以上): ")
        
        # 難易度
        difficulty_map = {
            '1': ('beginner', '初心者向け'),
            '2': ('intermediate', '経験者向け'),
            '3': ('expert', 'エキスパート向け')
        }
        
        self.print_with_encoding("\n難易度を選択:")
        for key, (_, text) in difficulty_map.items():
            self.print_with_encoding(f"  {key}: {text}")
        
        diff_choice = self.get_user_input("選択 (1-3): ", choices=['1', '2', '3'])
        game_data['difficulty'] = difficulty_map[diff_choice][0]
        game_data['difficultyText'] = difficulty_map[diff_choice][1]
        
        # 説明文
        description = self.get_user_input("ゲームの説明: ")
        game_data['description'] = description
        
        # ファイル名（提案付き）
        self.print_with_encoding(f"\n📁 ファイル設定（推奨値が表示されます）")
        
        image_file = self.get_user_input(
            f"画像ファイル名 [{suggestions['image']}]: ", 
            required=False
        ) or suggestions['image']
        if image_file:
            game_data['image'] = image_file
        
        # PDFファイルパス
        rules_url = self.get_user_input(
            f"ルール和訳PDFパス [{suggestions['rules']}]: ",
            required=False
        ) or suggestions['rules']
        
        summary_url = self.get_user_input(
            f"サマリーシートPDFパス [{suggestions['summary']}]: ",
            required=False
        ) or suggestions['summary']
        
        game_data['rulesUrl'] = rules_url
        game_data['summaryUrl'] = summary_url
        
        return game_data
    
    def preview_game(self, game_data):
        """追加予定のゲーム情報をプレビュー"""
        self.print_with_encoding("\n" + "="*50)
        self.print_with_encoding("📋 追加予定のゲーム情報:")
        self.print_with_encoding("="*50)
        for key, value in game_data.items():
            self.print_with_encoding(f"{key:15}: {value}")
        self.print_with_encoding("="*50)
        
        # ファイル存在チェック
        self.print_with_encoding("\n📁 ファイル存在チェック:")
        if game_data.get('image'):
            exists = self.check_file_exists(game_data['image'])
            status = "✅ 存在" if exists else "❌ 未配置"
            self.print_with_encoding(f"   画像: {status}")
        
        for field, label in [('rulesUrl', 'ルール'), ('summaryUrl', 'サマリー')]:
            if game_data.get(field):
                exists = self.check_file_exists(game_data[field])
                status = "✅ 存在" if exists else "❌ 未配置"
                self.print_with_encoding(f"   {label}: {status}")
    
    def run_add_game(self):
        """ゲーム追加のメイン処理"""
        try:
            # ディレクトリ作成
            self.ensure_directories()
            
            # 新しいゲーム情報を取得
            new_game = self.add_new_game()
            
            # プレビュー表示
            self.preview_game(new_game)
            
            # 確認
            confirm = self.get_user_input("\n追加しますか？ (y/n): ", choices=['y', 'n', 'Y', 'N'])
            if confirm.lower() != 'y':
                self.print_with_encoding("❌ キャンセルしました")
                return False
            
            # 既存データに追加
            data = self.load_games_data()
            data['games'].append(new_game)
            
            # 保存
            success = self.save_games_data(data)
            if not success:
                return False
            
            self.print_with_encoding(f"\n✅ '{new_game['title']}' を追加しました！")
            
            # 次のステップを表示
            self.show_next_steps(new_game)
            return True
            
        except KeyboardInterrupt:
            self.print_with_encoding("\n❌ 処理を中断しました")
            return False
        except Exception as e:
            self.print_with_encoding(f"❌ エラーが発生しました: {e}")
            return False
    
    def show_next_steps(self, game_data):
        """次に行うべき作業を表示"""
        self.print_with_encoding("\n📝 次のステップ:")
        
        steps = []
        if game_data.get('image') and not self.check_file_exists(game_data['image']):
            steps.append(f"1. 画像ファイル '{game_data['image']}' を docs\\assets\\images\\ に配置")
        
        if game_data.get('rulesUrl') and not self.check_file_exists(game_data['rulesUrl']):
            file_path = game_data['rulesUrl'].replace('/', '\\')
            steps.append(f"2. ルールPDF を docs{file_path} に配置")
        
        if game_data.get('summaryUrl') and not self.check_file_exists(game_data['summaryUrl']):
            file_path = game_data['summaryUrl'].replace('/', '\\')
            steps.append(f"3. サマリーPDF を docs{file_path} に配置")
        
        steps.extend([
            f"{len(steps)+1}. git add, commit, push でサイトを更新",
            f"{len(steps)+2}. ローカルで確認: bundle exec jekyll serve"
        ])
        
        for step in steps:
            self.print_with_encoding(f"   {step}")

def main():
    # Windows環境での文字化け対策
    if platform.system() == "Windows":
        os.system('chcp 65001 >nul 2>&1')  # UTF-8に設定
    
    parser = argparse.ArgumentParser(description='ボードゲームライブラリ管理ツール')
    parser.add_argument('--list', action='store_true', help='既存ゲーム一覧を表示')
    parser.add_argument('--validate', action='store_true', help='データ検証を実行')
    parser.add_argument('--add', action='store_true', help='新しいゲームを追加（デフォルト）')
    
    args = parser.parse_args()
    
    try:
        adder = GameAdder()
        
        if args.list:
            adder.list_games()
        elif args.validate:
            adder.validate_data()
        else:  # デフォルト動作または --add
            adder.run_add_game()
            
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()