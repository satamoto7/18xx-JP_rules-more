#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ボードゲーム管理ツール
ゲームの一覧表示、編集、削除、検索機能を提供
"""

import yaml
import os
import sys
import argparse
import platform
import shutil
from pathlib import Path
from datetime import datetime

class GameManager:
    def __init__(self):
        # scripts フォルダから docs フォルダへのパス
        self.script_dir = Path(__file__).parent  # scripts フォルダ
        self.docs_dir = self.script_dir.parent / "docs"  # docs フォルダ
        self.games_yml_path = self.docs_dir / "_data" / "games.yml"
        self.images_dir = self.docs_dir / "assets" / "images"
        self.downloads_dir = self.docs_dir / "downloads"
        self.is_windows = platform.system() == "Windows"
    
    def print_safe(self, text):
        """Windows環境での安全な出力"""
        try:
            print(text)
        except UnicodeEncodeError:
            safe_text = text.replace('🎲', '[GAME]').replace('🖼️', '[IMG]').replace('✅', '[OK]').replace('❌', '[ERROR]')
            print(safe_text)
    
    def load_games_data(self):
        """既存のゲームデータを読み込み"""
        if not self.games_yml_path.exists():
            self.print_safe("❌ games.yml ファイルが見つかりません")
            return {'games': []}
        
        try:
            with open(self.games_yml_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {'games': []}
        except Exception as e:
            self.print_safe(f"❌ ファイル読み込みエラー: {e}")
            return {'games': []}
    
    def save_games_data(self, data):
        """ゲームデータを保存"""
        try:
            # バックアップ作成
            if self.games_yml_path.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = self.games_yml_path.with_suffix(f'.yml.backup.{timestamp}')
                shutil.copy2(str(self.games_yml_path), str(backup_path))
                self.print_safe(f"📁 バックアップ作成: {backup_path.name}")
            
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
    
    def list_games(self, show_details=False):
        """登録済みゲーム一覧を表示"""
        data = self.load_games_data()
        games = data.get('games', [])
        
        if not games:
            self.print_safe("📝 登録されているゲームはありません")
            return []
        
        self.print_safe(f"🎲 登録済みゲーム一覧 ({len(games)}件)")
        self.print_safe("=" * 80)
        
        for i, game in enumerate(games, 1):
            title = game.get('title', 'タイトル不明')
            game_id = game.get('id', 'ID不明')
            players = game.get('players', '?')
            time = game.get('time', '?')
            difficulty = game.get('difficultyText', '?')
            
            self.print_safe(f"{i:2d}. {title}")
            
            if show_details:
                self.print_safe(f"     ID: {game_id}")
                self.print_safe(f"     プレイ人数: {players}")
                self.print_safe(f"     プレイ時間: {time}")
                self.print_safe(f"     難易度: {difficulty}")
                
                if game.get('description'):
                    desc = game['description']
                    if len(desc) > 60:
                        desc = desc[:57] + "..."
                    self.print_safe(f"     説明: {desc}")
                
                # ファイル状況
                files_status = []
                if game.get('image'):
                    image_path = self.images_dir / game['image']
                    status = "✅" if image_path.exists() else "❌"
                    files_status.append(f"画像{status}")
                
                if game.get('rulesUrl'):
                    rules_path = self.docs_dir / game['rulesUrl'][1:]
                    status = "✅" if rules_path.exists() else "❌"
                    files_status.append(f"ルール{status}")
                
                if game.get('summaryUrl'):
                    summary_path = self.docs_dir / game['summaryUrl'][1:]
                    status = "✅" if summary_path.exists() else "❌"
                    files_status.append(f"サマリー{status}")
                
                if files_status:
                    self.print_safe(f"     ファイル: {' | '.join(files_status)}")
                
                self.print_safe("")
            else:
                self.print_safe(f"     ID: {game_id} | {players} | {time} | {difficulty}")
        
        if not show_details:
            self.print_safe("\n詳細表示: python manage_games.py --list --details")
        
        return games
    
    def search_games(self, query):
        """ゲームを検索"""
        data = self.load_games_data()
        games = data.get('games', [])
        
        if not query:
            return games
        
        query_lower = query.lower()
        matches = []
        
        for game in games:
            # タイトル、ID、説明で検索
            searchable_fields = [
                game.get('title', ''),
                game.get('id', ''),
                game.get('description', ''),
                game.get('players', ''),
                game.get('difficultyText', '')
            ]
            
            if any(query_lower in field.lower() for field in searchable_fields):
                matches.append(game)
        
        return matches
    
    def find_game_by_id_or_title(self, query):
        """IDまたはタイトルでゲームを検索（管理操作用）"""
        data = self.load_games_data()
        games = data.get('games', [])
        
        # 完全一致検索
        for game in games:
            if (game.get('id', '').lower() == query.lower() or 
                game.get('title', '').lower() == query.lower()):
                return game
        
        # 部分一致検索
        matches = []
        for game in games:
            if (query.lower() in game.get('id', '').lower() or 
                query.lower() in game.get('title', '').lower()):
                matches.append(game)
        
        return matches
    
    def select_game_interactive(self, games, action="選択"):
        """ゲームをインタラクティブに選択"""
        if not games:
            self.print_safe("❌ 対象となるゲームがありません")
            return None
        
        if len(games) == 1:
            return games[0]
        
        self.print_safe(f"\n{action}するゲームを選択してください:")
        for i, game in enumerate(games, 1):
            self.print_safe(f"  {i}. {game.get('title')} (ID: {game.get('id')})")
        
        while True:
            choice = self.safe_input(f"番号を選択 (1-{len(games)}): ")
            if choice.isdigit() and 1 <= int(choice) <= len(games):
                return games[int(choice) - 1]
            self.print_safe("❌ 無効な選択です")
    
    def get_game_details(self, game):
        """ゲームの詳細情報を表示"""
        self.print_safe(f"\n📋 ゲーム詳細: {game.get('title')}")
        self.print_safe("=" * 50)
        
        fields = [
            ('id', 'ID'),
            ('title', 'タイトル'),
            ('players', 'プレイ人数'),
            ('time', 'プレイ時間'),
            ('age', '対象年齢'),
            ('difficultyText', '難易度'),
            ('description', '説明'),
            ('image', '画像ファイル'),
            ('rulesUrl', 'ルールPDF'),
            ('summaryUrl', 'サマリーPDF')
        ]
        
        for field_key, field_name in fields:
            value = game.get(field_key, '(未設定)')
            if field_key == 'description' and len(str(value)) > 80:
                # 長い説明は折り返し
                self.print_safe(f"{field_name:12}: {str(value)[:77]}...")
                self.print_safe(f"             {str(value)[77:]}")
            else:
                self.print_safe(f"{field_name:12}: {value}")
        
        # ファイル存在確認
        self.print_safe("\n📁 ファイル状況:")
        
        if game.get('image'):
            image_path = self.images_dir / game['image']
            status = "✅ 存在" if image_path.exists() else "❌ 不在"
            self.print_safe(f"  画像ファイル: {status}")
        
        if game.get('rulesUrl'):
            rules_path = self.docs_dir / game['rulesUrl'][1:]
            status = "✅ 存在" if rules_path.exists() else "❌ 不在"
            self.print_safe(f"  ルールPDF:   {status}")
        
        if game.get('summaryUrl'):
            summary_path = self.docs_dir / game['summaryUrl'][1:]
            status = "✅ 存在" if summary_path.exists() else "❌ 不在"
            self.print_safe(f"  サマリーPDF: {status}")
    
    def edit_game(self, target_game_query=None):
        """ゲーム情報を編集"""
        if target_game_query:
            # コマンドライン引数で指定された場合
            matches = self.search_games(target_game_query)
            if not matches:
                self.print_safe(f"❌ '{target_game_query}' に一致するゲームが見つかりません")
                return False
            target_game = self.select_game_interactive(matches, "編集")
        else:
            # インタラクティブ選択
            games = self.list_games()
            if not games:
                return False
            
            self.print_safe("\n✏️ ゲーム情報を編集します")
            query = self.safe_input("編集するゲームのID、タイトル、または番号を入力: ")
            
            if not query:
                self.print_safe("❌ キャンセルしました")
                return False
            
            if query.isdigit():
                index = int(query) - 1
                if 0 <= index < len(games):
                    target_game = games[index]
                else:
                    self.print_safe("❌ 無効な番号です")
                    return False
            else:
                matches = self.search_games(query)
                if not matches:
                    self.print_safe(f"❌ '{query}' に一致するゲームが見つかりません")
                    return False
                target_game = self.select_game_interactive(matches, "編集")
        
        if not target_game:
            return False
        
        # 現在の情報を表示
        self.get_game_details(target_game)
        
        # 編集メニュー
        fields = [
            ('title', 'ゲーム名'),
            ('players', 'プレイ人数'),
            ('time', 'プレイ時間'),
            ('age', '対象年齢'),
            ('difficulty', '難易度'),
            ('description', '説明'),
            ('image', '画像ファイル名'),
            ('rulesUrl', 'ルールPDFパス'),
            ('summaryUrl', 'サマリーPDFパス')
        ]
        
        self.print_safe("\n✏️ 編集可能な項目:")
        for i, (field, name) in enumerate(fields, 1):
            self.print_safe(f"  {i}. {name}")
        self.print_safe("  0. 編集完了")
        
        # データ読み込み（最新状態を取得）
        data = self.load_games_data()
        target_index = None
        for i, game in enumerate(data['games']):
            if game.get('id') == target_game.get('id'):
                target_index = i
                break
        
        if target_index is None:
            self.print_safe("❌ ゲームデータが見つかりません")
            return False
        
        modified = False
        
        while True:
            choice = self.safe_input("\n編集する項目番号 (0で終了): ")
            
            if choice == '0':
                break
            
            if not choice.isdigit() or not (1 <= int(choice) <= len(fields)):
                self.print_safe("❌ 無効な選択です")
                continue
            
            field_index = int(choice) - 1
            field_key, field_name = fields[field_index]
            current_value = data['games'][target_index].get(field_key, '')
            
            self.print_safe(f"\n{field_name}の編集")
            self.print_safe(f"現在値: {current_value}")
            
            if field_key == 'difficulty':
                # 難易度は特別処理
                difficulty_map = {
                    '1': ('beginner', '初心者向け'),
                    '2': ('intermediate', '経験者向け'),
                    '3': ('expert', 'エキスパート向け')
                }
                
                self.print_safe("難易度を選択:")
                for key, (_, text) in difficulty_map.items():
                    self.print_safe(f"  {key}: {text}")
                
                new_choice = self.safe_input("選択 (1-3、空欄で変更なし): ")
                if new_choice in difficulty_map:
                    data['games'][target_index]['difficulty'] = difficulty_map[new_choice][0]
                    data['games'][target_index]['difficultyText'] = difficulty_map[new_choice][1]
                    modified = True
                    self.print_safe(f"✅ {field_name}を更新しました")
            else:
                new_value = self.safe_input(f"新しい値 (空欄で変更なし): ")
                if new_value:
                    data['games'][target_index][field_key] = new_value
                    modified = True
                    self.print_safe(f"✅ {field_name}を更新しました")
        
        # 保存
        if modified:
            if self.save_games_data(data):
                self.print_safe(f"\n✅ '{target_game.get('title')}' の編集が完了しました")
                return True
            else:
                self.print_safe("❌ 保存に失敗しました")
                return False
        else:
            self.print_safe("📝 変更はありませんでした")
            return True
    
    def delete_game(self, target_game_query=None):
        """ゲームを削除"""
        if target_game_query:
            # コマンドライン引数で指定された場合
            matches = self.search_games(target_game_query)
            if not matches:
                self.print_safe(f"❌ '{target_game_query}' に一致するゲームが見つかりません")
                return False
            target_game = self.select_game_interactive(matches, "削除")
        else:
            # インタラクティブ選択
            games = self.list_games()
            if not games:
                return False
            
            self.print_safe("\n🗑️ ゲームを削除します")
            query = self.safe_input("削除するゲームのID、タイトル、または番号を入力: ")
            
            if not query:
                self.print_safe("❌ キャンセルしました")
                return False
            
            if query.isdigit():
                index = int(query) - 1
                if 0 <= index < len(games):
                    target_game = games[index]
                else:
                    self.print_safe("❌ 無効な番号です")
                    return False
            else:
                matches = self.search_games(query)
                if not matches:
                    self.print_safe(f"❌ '{query}' に一致するゲームが見つかりません")
                    return False
                target_game = self.select_game_interactive(matches, "削除")
        
        if not target_game:
            return False
        
        # 削除対象の詳細表示
        self.get_game_details(target_game)
        
        # 削除確認
        self.print_safe(f"\n🗑️ 削除対象: {target_game.get('title')} (ID: {target_game.get('id')})")
        confirm = self.safe_input("本当に削除しますか？ (yes/no): ").lower()
        
        if confirm not in ['yes', 'y']:
            self.print_safe("❌ キャンセルしました")
            return False
        
        # 削除実行
        data = self.load_games_data()
        original_count = len(data['games'])
        data['games'] = [g for g in data['games'] if g.get('id') != target_game.get('id')]
        
        if len(data['games']) < original_count:
            if self.save_games_data(data):
                self.print_safe(f"✅ '{target_game.get('title')}' を削除しました")
                
                # 関連ファイルの削除確認
                self.suggest_file_cleanup(target_game)
                return True
            else:
                self.print_safe("❌ 削除に失敗しました")
                return False
        else:
            self.print_safe("❌ ゲームが見つからず、削除できませんでした")
            return False
    
    def suggest_file_cleanup(self, game_data):
        """削除されたゲームの関連ファイル削除を提案"""
        files_to_check = []
        
        if game_data.get('image'):
            image_path = self.images_dir / game_data['image']
            if image_path.exists():
                files_to_check.append(('画像', str(image_path)))
        
        if game_data.get('rulesUrl'):
            rules_path = self.docs_dir / game_data['rulesUrl'][1:]
            if rules_path.exists():
                files_to_check.append(('ルールPDF', str(rules_path)))
        
        if game_data.get('summaryUrl'):
            summary_path = self.docs_dir / game_data['summaryUrl'][1:]
            if summary_path.exists():
                files_to_check.append(('サマリーPDF', str(summary_path)))
        
        if files_to_check:
            self.print_safe("\n🗑️ 関連ファイルも削除しますか？")
            for file_type, file_path in files_to_check:
                self.print_safe(f"   {file_type}: {file_path}")
            
            delete_files = self.safe_input("ファイルも削除する場合は 'yes' を入力: ").lower()
            if delete_files == 'yes':
                for file_type, file_path in files_to_check:
                    try:
                        os.remove(file_path)
                        self.print_safe(f"✅ {file_type}を削除しました")
                    except Exception as e:
                        self.print_safe(f"❌ {file_type}削除エラー: {e}")
    
    def show_statistics(self):
        """統計情報を表示"""
        data = self.load_games_data()
        games = data.get('games', [])
        
        if not games:
            self.print_safe("📊 統計データがありません")
            return
        
        self.print_safe("📊 ボードゲームライブラリ統計")
        self.print_safe("=" * 40)
        
        # 基本統計
        self.print_safe(f"総ゲーム数: {len(games)}")
        
        # 難易度別統計
        difficulty_counts = {}
        for game in games:
            diff = game.get('difficultyText', '不明')
            difficulty_counts[diff] = difficulty_counts.get(diff, 0) + 1
        
        self.print_safe("\n難易度別:")
        for diff, count in sorted(difficulty_counts.items()):
            percentage = (count / len(games)) * 100
            self.print_safe(f"  {diff}: {count}件 ({percentage:.1f}%)")
        
        # プレイ人数分析
        player_ranges = []
        for game in games:
            players = game.get('players', '')
            if players:
                player_ranges.append(players)
        
        if player_ranges:
            self.print_safe(f"\nプレイ人数パターン: {len(set(player_ranges))}種類")
            
        # ファイル存在統計
        image_count = sum(1 for game in games if game.get('image') and 
                         (self.images_dir / game['image']).exists())
        rules_count = sum(1 for game in games if game.get('rulesUrl'))
        summary_count = sum(1 for game in games if game.get('summaryUrl'))
        
        self.print_safe(f"\nファイル統計:")
        self.print_safe(f"  画像ファイル: {image_count}/{len(games)} ({(image_count/len(games)*100):.1f}%)")
        self.print_safe(f"  ルールPDF:   {rules_count}/{len(games)} ({(rules_count/len(games)*100):.1f}%)")
        self.print_safe(f"  サマリーPDF: {summary_count}/{len(games)} ({(summary_count/len(games)*100):.1f}%)")


def main():
    parser = argparse.ArgumentParser(description='ボードゲーム管理ツール')
    parser.add_argument('--list', action='store_true', help='ゲーム一覧を表示')
    parser.add_argument('--details', action='store_true', help='詳細情報も表示（--listと併用）')
    parser.add_argument('--search', type=str, help='ゲームを検索')
    parser.add_argument('--edit', type=str, nargs='?', const='', help='ゲーム情報を編集')
    parser.add_argument('--delete', type=str, nargs='?', const='', help='ゲームを削除')
    parser.add_argument('--show', type=str, help='特定ゲームの詳細を表示')
    parser.add_argument('--stats', action='store_true', help='統計情報を表示')
    
    args = parser.parse_args()
    
    # Windows環境での文字化け対策
    if platform.system() == "Windows":
        os.system('chcp 65001 >nul 2>&1')
    
    manager = GameManager()
    
    try:
        if args.list:
            manager.list_games(show_details=args.details)
        elif args.search:
            matches = manager.search_games(args.search)
            if matches:
                manager.print_safe(f"🔍 検索結果: '{args.search}' ({len(matches)}件)")
                manager.print_safe("=" * 50)
                for i, game in enumerate(matches, 1):
                    manager.print_safe(f"{i}. {game.get('title')} (ID: {game.get('id')})")
                    if game.get('description'):
                        desc = game['description']
                        if len(desc) > 60:
                            desc = desc[:57] + "..."
                        manager.print_safe(f"   {desc}")
            else:
                manager.print_safe(f"❌ '{args.search}' に一致するゲームが見つかりません")
        elif args.edit is not None:
            manager.edit_game(args.edit if args.edit else None)
        elif args.delete is not None:
            manager.delete_game(args.delete if args.delete else None)
        elif args.show:
            matches = manager.search_games(args.show)
            if matches:
                target_game = manager.select_game_interactive(matches, "表示") if len(matches) > 1 else matches[0]
                if target_game:
                    manager.get_game_details(target_game)
            else:
                manager.print_safe(f"❌ '{args.show}' に一致するゲームが見つかりません")
        elif args.stats:
            manager.show_statistics()
        else:
            # デフォルト：使用方法を表示
            manager.print_safe("🎲 ボードゲーム管理ツール")
            manager.print_safe("=" * 30)
            manager.print_safe("使用方法:")
            manager.print_safe("  python manage_games.py --list              # ゲーム一覧")
            manager.print_safe("  python manage_games.py --list --details    # 詳細付き一覧")
            manager.print_safe("  python manage_games.py --search 'キーワード' # 検索")
            manager.print_safe("  python manage_games.py --edit              # 編集")
            manager.print_safe("  python manage_games.py --edit 'ゲーム名'    # 特定ゲーム編集")
            manager.print_safe("  python manage_games.py --delete            # 削除")
            manager.print_safe("  python manage_games.py --show 'ゲーム名'    # 詳細表示")
            manager.print_safe("  python manage_games.py --stats             # 統計情報")
            manager.print_safe("\n新しいゲームの追加:")
            manager.print_safe("  python add_game.py")
            
            # 簡単な統計も表示
            data = manager.load_games_data()
            game_count = len(data.get('games', []))
            manager.print_safe(f"\n現在のゲーム数: {game_count}件")
    
    except KeyboardInterrupt:
        manager.print_safe("\n❌ 処理を中断しました")
    except Exception as e:
        manager.print_safe(f"❌ エラーが発生しました: {e}")

if __name__ == "__main__":
    main()