#!/usr/bin/env python3

"""
Interactive thread cleanup tool with categorization and selective deletion
Provides better observability and control over what gets deleted
"""

import sys
import argparse
import asyncio
import aiohttp
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse


class ThreadCleanup:
    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {'Content-Type': 'application/json'}
        if api_key:
            self.headers['X-Api-Key'] = api_key

    def ask_question(self, question: str) -> str:
        """Ask user for input"""
        return input(question)

    def categorize_threads(self, threads: List[Dict]) -> Dict:
        """Categorize threads by status, runs, and graph ID"""
        categories = {
            'byGraph': {},
            'byStatus': {},
            'byRuns': {}
        }

        for thread in threads:
            run_count = len(thread.get('runs', []))
            status = thread.get('status', 'unknown')

            # Graph categorization
            if thread.get('metadata') and thread['metadata'].get('graph_id'):
                graph_id = thread['metadata']['graph_id']
                if graph_id not in categories['byGraph']:
                    categories['byGraph'][graph_id] = []
                categories['byGraph'][graph_id].append(thread)

            # Status categorization
            if status not in categories['byStatus']:
                categories['byStatus'][status] = []
            categories['byStatus'][status].append(thread)

            # Runs categorization
            if run_count == 0:
                runs_category = '0 runs'
            elif run_count == 1:
                runs_category = '1 run'
            elif run_count < 5:
                runs_category = f'{run_count} runs'
            elif run_count < 10:
                runs_category = '5-9 runs'
            elif run_count < 20:
                runs_category = '10-19 runs'
            else:
                runs_category = '20+ runs'

            if runs_category not in categories['byRuns']:
                categories['byRuns'][runs_category] = []
            categories['byRuns'][runs_category].append(thread)

        # Add allThreads for easy access
        categories['allThreads'] = threads
        return categories

    def display_thread_summary(self, thread: Dict) -> str:
        """Display summary of a single thread"""
        created_at = thread.get('created_at', 'Unknown')
        if created_at != 'Unknown':
            try:
                dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                created_at = dt.isoformat()
            except:
                pass

        status = thread.get('status', 'unknown')
        run_count = len(thread.get('runs', []))
        metadata = json.dumps(thread.get('metadata', {})) if thread.get('metadata') else 'None'

        return f"""  ID: {thread.get('thread_id', 'Unknown')}
  Created: {created_at}
  Status: {status}
  Runs: {run_count}
  Metadata: {metadata}"""

    def display_categories(self, categories: Dict) -> None:
        """Display thread categories"""
        print(f"\n📋 Total threads found: {len(categories['allThreads'])}")

        if categories['byStatus']:
            print('\n📝 By Status:')
            for status, threads in categories['byStatus'].items():
                status_icons = {
                    'idle': '😴',
                    'running': '🏃',
                    'completed': '✅',
                    'failed': '❌',
                    'pending': '⏳'
                }
                icon = status_icons.get(status, '❓')
                print(f'├─ {icon} {status}: {len(threads)}')

        if categories['byRuns']:
            print('\n🏃 By Runs:')
            for run_category, threads in categories['byRuns'].items():
                if run_category == '0 runs':
                    icon = '🚫'
                elif run_category == '1 run':
                    icon = '1️⃣'
                elif '20+' in run_category:
                    icon = '🔥'
                else:
                    icon = '🔢'
                print(f'├─ {icon} {run_category}: {len(threads)}')

        if categories['byGraph']:
            print('\n🔧 By Graph ID:')
            for graph_id, threads in categories['byGraph'].items():
                print(f'├─ 📊 {graph_id}: {len(threads)}')

    async def select_threads_to_delete(self, categories: Dict, all_threads: List[Dict]) -> Optional[List[Dict]]:
        """Main menu for selecting what to delete"""
        print('\n🎯 What would you like to delete?')
        print('1. ⏰ Delete by TIME')
        print('2. 📝 Delete by STATUS')
        print('3. 🏃 Delete by RUNS COUNT')
        print('4. 🔧 Delete by GRAPH ID')
        print('5. 👁️  PREVIEW all threads')
        print('6. ⚠️  Delete ALL threads - DANGEROUS!')
        print('7. 🚪 Exit without deleting')

        choice = self.ask_question('\nSelect option (1-7): ')

        if choice == '1':
            return await self.select_by_time(all_threads)
        elif choice == '2':
            return await self.select_by_status(categories['byStatus'], all_threads)
        elif choice == '3':
            categories_with_runs = self.categorize_threads(all_threads)
            return await self.select_by_runs(categories_with_runs['byRuns'], all_threads)
        elif choice == '4':
            categories_with_graph = self.categorize_threads(all_threads)
            return await self.select_by_graph(categories_with_graph['byGraph'], all_threads)
        elif choice == '5':
            return await self.preview_all_threads(all_threads)
        elif choice == '6':
            return await self.confirm_delete_all(all_threads)
        elif choice == '7':
            print('Exiting without deleting anything.')
            return None
        else:
            print('Invalid choice. Exiting.')
            return None

    async def preview_all_threads(self, all_threads: List[Dict]) -> List[Dict]:
        """Preview all threads without filtering"""
        print(f'\n👁️  Previewing all {len(all_threads)} threads:')

        if len(all_threads) == 0:
            print('No threads found.')
            print('1. 🚪 Go back to main menu')
            self.ask_question('\nSelect option (1): ')
            full_categories = self.categorize_threads(all_threads)
            return await self.select_threads_to_delete(full_categories, all_threads)

        threads_per_page = 5
        start_index = 0

        while start_index < len(all_threads):
            end_index = min(start_index + threads_per_page, len(all_threads))
            page_threads = all_threads[start_index:end_index]

            print(f'\n--- All Threads {start_index + 1}-{end_index} of {len(all_threads)} ---')

            for i, thread in enumerate(page_threads):
                print(f'\n[{start_index + i + 1}]')
                print(self.display_thread_summary(thread))

            if end_index < len(all_threads):
                print('\n1. Continue to next page')
                print('2. 🚪 Go back to main menu')

                choice = self.ask_question('\nSelect option (1-2): ')

                if choice == '1':
                    start_index = end_index
                    continue
                elif choice == '2':
                    full_categories = self.categorize_threads(all_threads)
                    return await self.select_threads_to_delete(full_categories, all_threads)
                else:
                    start_index = end_index
                    continue
            else:
                print('\n--- End of all threads ---')
                print('1. 🚪 Go back to main menu')
                self.ask_question('\nSelect option (1): ')
                full_categories = self.categorize_threads(all_threads)
                return await self.select_threads_to_delete(full_categories, all_threads)

        return []

    async def select_by_time(self, all_threads: List[Dict]) -> Optional[List[Dict]]:
        """Select threads by time"""
        print('\n⏰ Delete threads created:')
        print('1. Within the last hour')
        print('2. Within the last week')
        print('3. Within the last month')
        print('4. All time (any date)')
        print('5. Custom date range')
        print('6. 🚪 Go back to main menu')

        choice = self.ask_question('\nSelect time option (1-6): ')

        now = datetime.now(timezone.utc)

        if choice == '1':
            start_time = now.timestamp() - (60 * 60)  # 1 hour ago
            end_time = now.timestamp()
        elif choice == '2':
            start_time = now.timestamp() - (7 * 24 * 60 * 60)  # 1 week ago
            end_time = now.timestamp()
        elif choice == '3':
            start_time = now.timestamp() - (30 * 24 * 60 * 60)  # 1 month ago
            end_time = now.timestamp()
        elif choice == '4':
            start_time = 0  # All time
            end_time = now.timestamp()
        elif choice == '5':
            return await self.select_custom_date_range(all_threads)
        elif choice == '6':
            full_categories = self.categorize_threads(all_threads)
            return await self.select_threads_to_delete(full_categories, all_threads)
        else:
            print('Invalid choice. Going back.')
            return await self.select_by_time(all_threads)

        # Filter threads by time range
        threads_to_delete = []
        for thread in all_threads:
            created_at = thread.get('created_at')
            if created_at:
                try:
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    thread_time = dt.timestamp()
                    if start_time <= thread_time <= end_time:
                        threads_to_delete.append(thread)
                except:
                    continue

        time_range_desc = {
            '1': 'within the last hour',
            '2': 'within the last week',
            '3': 'within the last month',
            '4': 'from all time'
        }.get(choice, 'from selected time range')

        print(f'\nFound {len(threads_to_delete)} threads created {time_range_desc}.')

        if len(threads_to_delete) == 0:
            print('No threads match your time criteria.')
            return await self.select_by_time(all_threads)

        # Ask if they want to review before deleting
        print('\nDo you want to:')
        print('1. 👁️  Review threads before deleting')
        print('2. Delete immediately')
        print('3. 🚪 Go back to main menu')

        review_choice = self.ask_question('\nSelect option (1-3): ')

        if review_choice == '1':
            return await self.review_threads(threads_to_delete, time_range_desc, all_threads)
        elif review_choice == '2':
            return threads_to_delete
        elif review_choice == '3':
            return await self.select_by_time(all_threads)
        else:
            return threads_to_delete

    async def select_custom_date_range(self, all_threads: List[Dict]) -> Optional[List[Dict]]:
        """Select threads by custom cutoff date"""
        print('\n📅 Delete threads created before a specific date:')
        print('Enter date in format: YYYY-MM-DD HH:MM (24-hour format)')
        print('Or just YYYY-MM-DD for whole day')
        print('Example: 2024-01-15 14:30 or 2024-01-15')
        print('All threads created BEFORE this date will be deleted.\n')

        cutoff_date = self.ask_question('Delete threads created before: ')

        try:
            if ' ' in cutoff_date:
                cutoff_time = datetime.fromisoformat(cutoff_date).timestamp()
            else:
                cutoff_time = datetime.fromisoformat(cutoff_date + ' 00:00:00').timestamp()

            if cutoff_time > datetime.now().timestamp():
                print('❌ Cutoff date cannot be in the future.')
                return await self.select_custom_date_range(all_threads)

        except ValueError:
            print('❌ Invalid date format. Please use YYYY-MM-DD or YYYY-MM-DD HH:MM')
            return await self.select_custom_date_range(all_threads)

        # Filter threads created before the cutoff date
        threads_to_delete = []
        for thread in all_threads:
            created_at = thread.get('created_at')
            if created_at:
                try:
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    if dt.timestamp() < cutoff_time:
                        threads_to_delete.append(thread)
                except:
                    continue

        cutoff_str = datetime.fromtimestamp(cutoff_time).strftime('%m/%d/%Y, %I:%M:%S %p')
        print(f'\nFound {len(threads_to_delete)} threads created before {cutoff_str}.')

        if len(threads_to_delete) == 0:
            print('No threads were created before this date.')
            print('1. Try different date')
            print('2. 🚪 Go back to time menu')

            choice = self.ask_question('\nSelect option (1-2): ')

            if choice == '1':
                return await self.select_custom_date_range(all_threads)
            else:
                return await self.select_by_time(all_threads)

        # Ask if they want to review before deleting
        print('\nDo you want to:')
        print('1. 👁️  Review threads before deleting')
        print('2. Delete immediately')
        print('3. Try different date')
        print('4. 🚪 Go back to time menu')

        review_choice = self.ask_question('\nSelect option (1-4): ')

        if review_choice == '1':
            return await self.review_threads(threads_to_delete, f'created before {cutoff_str}', all_threads)
        elif review_choice == '2':
            return threads_to_delete
        elif review_choice == '3':
            return await self.select_custom_date_range(all_threads)
        elif review_choice == '4':
            return await self.select_by_time(all_threads)
        else:
            return threads_to_delete

    async def review_threads(self, threads: List[Dict], description: str = '', all_threads: Optional[List[Dict]] = None) -> List[Dict]:
        """Review threads before deletion"""
        description_text = f' {description}' if description else ''
        print(f'\n👁️  Reviewing {len(threads)} threads{description_text}:')

        threads_per_page = 5
        start_index = 0

        while start_index < len(threads):
            end_index = min(start_index + threads_per_page, len(threads))
            page_threads = threads[start_index:end_index]

            print(f'\n--- Threads {start_index + 1}-{end_index} of {len(threads)} ---')

            for i, thread in enumerate(page_threads):
                print(f'\n[{start_index + i + 1}]')
                print(self.display_thread_summary(thread))

            if end_index < len(threads):
                print('\n1. Continue to next page')
                print('2. Delete all these threads')
                print('3. 🚪 Cancel and return to main menu')

                choice = self.ask_question('\nSelect option (1-3): ')

                if choice == '1':
                    start_index = end_index
                    continue
                elif choice == '2':
                    return threads
                elif choice == '3':
                    if all_threads:
                        full_categories = self.categorize_threads(all_threads)
                        return await self.select_threads_to_delete(full_categories, all_threads)
                    return []
                else:
                    start_index = end_index
                    continue
            else:
                print('\n--- End of threads ---')
                print('1. Delete all reviewed threads')
                print('2. 🚪 Cancel and return to main menu')

                choice = self.ask_question('\nSelect option (1-2): ')

                if choice == '1':
                    return threads
                elif choice == '2':
                    if all_threads:
                        full_categories = self.categorize_threads(all_threads)
                        return await self.select_threads_to_delete(full_categories, all_threads)
                    return []
                else:
                    return threads

        return threads

    async def confirm_delete_all(self, all_threads: List[Dict]) -> List[Dict]:
        """Confirm deletion of all threads"""
        print(f'\n⚠️  WARNING: You are about to delete ALL {len(all_threads)} threads!')
        print('This action cannot be undone.')
        print('\n1. Continue with deletion')
        print('2. 🚪 Go back to main menu')

        initial_choice = self.ask_question('\nSelect option (1-2): ')

        if initial_choice != '1':
            full_categories = self.categorize_threads(all_threads)
            return await self.select_threads_to_delete(full_categories, all_threads)

        confirm1 = self.ask_question('\nType "DELETE ALL" to confirm: ')
        if confirm1 != 'DELETE ALL':
            print('Confirmation failed. Returning to main menu.')
            full_categories = self.categorize_threads(all_threads)
            return await self.select_threads_to_delete(full_categories, all_threads)

        confirm2 = self.ask_question(f'\nFinal confirmation: Delete all {len(all_threads)} threads? (yes/no): ')
        if confirm2.lower() != 'yes':
            print('Deletion cancelled. Returning to main menu.')
            full_categories = self.categorize_threads(all_threads)
            return await self.select_threads_to_delete(full_categories, all_threads)

        return all_threads

    async def select_by_status(self, by_status: Dict, all_threads: List[Dict]) -> Optional[List[Dict]]:
        """Select threads by status"""
        print('\n📝 Select Status:')
        statuses = list(by_status.keys())
        for i, status in enumerate(statuses):
            status_icons = {
                'idle': '😴',
                'running': '🏃',
                'completed': '✅',
                'failed': '❌',
                'pending': '⏳'
            }
            icon = status_icons.get(status, '❓')
            print(f'{i + 1}. {icon} {status} ({len(by_status[status])} threads)')
        print(f'{len(statuses) + 1}. 🚪 Go back to main menu')

        choice = self.ask_question(f'Select status (1-{len(statuses) + 1}): ')
        index = int(choice) - 1

        if 0 <= index < len(statuses):
            selected_status = statuses[index]
            threads_to_delete = by_status[selected_status]

            print(f'\nFound {len(threads_to_delete)} threads with status "{selected_status}".')

            # Ask if they want to review before deleting
            print('\nDo you want to:')
            print('1. 👁️  Review threads before deleting')
            print('2. Delete immediately')
            print('3. 🚪 Go back to status menu')

            review_choice = self.ask_question('\nSelect option (1-3): ')

            if review_choice == '1':
                return await self.review_threads(threads_to_delete, f'with status "{selected_status}"', all_threads)
            elif review_choice == '2':
                return threads_to_delete
            elif review_choice == '3':
                return await self.select_by_status(by_status, all_threads)
            else:
                return threads_to_delete
        elif index == len(statuses):
            # Go back to main menu
            full_categories = self.categorize_threads(all_threads)
            return await self.select_threads_to_delete(full_categories, all_threads)

        return []

    async def select_by_runs(self, by_runs: Dict, all_threads: List[Dict]) -> Optional[List[Dict]]:
        """Select threads by runs count"""
        print('\n🏃 Select by Runs Count:')

        # Sort categories properly
        runs_categories = list(by_runs.keys())
        def get_runs_value(category):
            if category == '0 runs':
                return 0
            elif category == '1 run':
                return 1
            elif '-' in category:
                return int(category.split('-')[0])
            elif category == '20+ runs':
                return 20
            else:
                try:
                    return int(category.split()[0])
                except:
                    return 0

        runs_categories.sort(key=get_runs_value)

        for i, category in enumerate(runs_categories):
            if category == '0 runs':
                icon = '🚫'
            elif category == '1 run':
                icon = '1️⃣'
            elif '20+' in category:
                icon = '🔥'
            else:
                icon = '🔢'
            print(f'{i + 1}. {icon} {category} ({len(by_runs[category])} threads)')
        print(f'{len(runs_categories) + 1}. 🚪 Go back to main menu')

        choice = self.ask_question(f'Select runs category (1-{len(runs_categories) + 1}): ')
        index = int(choice) - 1

        if 0 <= index < len(runs_categories):
            selected_category = runs_categories[index]
            threads_to_delete = by_runs[selected_category]

            print(f'\nFound {len(threads_to_delete)} threads with {selected_category}.')

            # Ask if they want to review before deleting
            print('\nDo you want to:')
            print('1. 👁️  Review threads before deleting')
            print('2. Delete immediately')
            print('3. 🚪 Go back to runs menu')

            review_choice = self.ask_question('\nSelect option (1-3): ')

            if review_choice == '1':
                return await self.review_threads(threads_to_delete, f'with {selected_category}', all_threads)
            elif review_choice == '2':
                return threads_to_delete
            elif review_choice == '3':
                return await self.select_by_runs(by_runs, all_threads)
            else:
                return threads_to_delete
        elif index == len(runs_categories):
            # Go back to main menu
            full_categories = self.categorize_threads(all_threads)
            return await self.select_threads_to_delete(full_categories, all_threads)

        return []

    async def select_by_graph(self, by_graph: Dict, all_threads: List[Dict]) -> Optional[List[Dict]]:
        """Select threads by graph ID"""
        print('\n🔧 Select by Graph ID:')
        graphs = list(by_graph.keys())
        for i, graph in enumerate(graphs):
            print(f'{i + 1}. 📊 {graph} ({len(by_graph[graph])} threads)')
        print(f'{len(graphs) + 1}. 🚪 Go back to main menu')

        choice = self.ask_question(f'Select graph (1-{len(graphs) + 1}): ')
        index = int(choice) - 1

        if 0 <= index < len(graphs):
            selected_graph = graphs[index]
            threads_to_delete = by_graph[selected_graph]

            print(f'\nFound {len(threads_to_delete)} threads for graph "{selected_graph}".')

            # Ask if they want to review before deleting
            print('\nDo you want to:')
            print('1. 👁️  Review threads before deleting')
            print('2. Delete immediately')
            print('3. 🚪 Go back to graphs menu')

            review_choice = self.ask_question('\nSelect option (1-3): ')

            if review_choice == '1':
                return await self.review_threads(threads_to_delete, f'for graph "{selected_graph}"', all_threads)
            elif review_choice == '2':
                return threads_to_delete
            elif review_choice == '3':
                return await self.select_by_graph(by_graph, all_threads)
            else:
                return threads_to_delete
        elif index == len(graphs):
            # Go back to main menu
            full_categories = self.categorize_threads(all_threads)
            return await self.select_threads_to_delete(full_categories, all_threads)

        return []

    async def delete_threads(self, threads_to_delete: List[Dict]) -> int:
        """Delete the selected threads"""
        if not threads_to_delete or len(threads_to_delete) == 0:
            return 0

        print(f'\n🗑️  Deleting {len(threads_to_delete)} threads...')

        confirm = self.ask_question(f'Are you sure you want to delete {len(threads_to_delete)} threads? (yes/no): ')
        if confirm.lower() != 'yes':
            print('Deletion cancelled.')
            return 0

        deleted = 0
        failed = 0

        async with aiohttp.ClientSession(headers=self.headers) as session:
            for thread in threads_to_delete:
                try:
                    delete_url = f"{self.base_url}/threads/{thread['thread_id']}"
                    async with session.delete(delete_url) as response:
                        if not response.ok:
                            print(f"❌ Failed to delete thread {thread['thread_id']}: {response.status} {response.reason}")
                            failed += 1
                        else:
                            deleted += 1
                            print(f"✅ Deleted: {deleted}/{len(threads_to_delete)}", end='\r')
                except Exception as delete_error:
                    print(f"❌ Error deleting thread {thread['thread_id']}: {delete_error}")
                    failed += 1

        print(f'\n\n📈 Summary: {deleted} deleted, {failed} failed')
        return deleted

    async def interactive_clean(self) -> None:
        """Main interactive cleanup function"""
        try:
            print('🔍 Discovering threads...')
            print(f'📡 Connecting to: {self.base_url}')

            # Try different endpoint variations to find the correct one
            endpoints_to_try = [
                {'url': f'{self.base_url}/threads/search', 'method': 'POST', 'body': {'limit': 1000, 'offset': 0}},
                {'url': f'{self.base_url}/threads', 'method': 'GET', 'body': None},
                {'url': f'{self.base_url}/threads?limit=1000', 'method': 'GET', 'body': None}
            ]

            search_response = None
            working_endpoint = None

            async with aiohttp.ClientSession(headers=self.headers) as session:
                for endpoint in endpoints_to_try:
                    print(f"🔍 Trying {endpoint['method']} {endpoint['url']}")

                    try:
                        if endpoint['method'] == 'POST':
                            async with session.post(endpoint['url'], json=endpoint['body']) as response:
                                if response.ok:
                                    search_response = response
                                    working_endpoint = endpoint
                                    print(f"✅ Found working endpoint: {endpoint['method']} {endpoint['url']}")
                                    break
                                else:
                                    print(f"❌ {endpoint['method']} {endpoint['url']} failed: {response.status} {response.reason}")
                                    if response.status in [401, 403]:
                                        error_text = await response.text()
                                        print(f"   Error details: {error_text}")
                        else:
                            async with session.get(endpoint['url']) as response:
                                if response.ok:
                                    search_response = response
                                    working_endpoint = endpoint
                                    print(f"✅ Found working endpoint: {endpoint['method']} {endpoint['url']}")
                                    break
                                else:
                                    print(f"❌ {endpoint['method']} {endpoint['url']} failed: {response.status} {response.reason}")
                                    if response.status in [401, 403]:
                                        error_text = await response.text()
                                        print(f"   Error details: {error_text}")
                    except Exception as fetch_error:
                        print(f"❌ {endpoint['method']} {endpoint['url']} error: {fetch_error}")

                if not search_response or not working_endpoint:
                    print('\n❌ None of the thread endpoints worked. Please check:')
                    print('1. Your server URL is correct')
                    print('2. Your API key has the right permissions')
                    print('3. The server is running and accessible')
                    raise Exception('Could not find a working threads endpoint')

                # Get all threads first
                all_threads = []
                has_more = True
                offset = 0

                while has_more:
                    if working_endpoint['method'] == 'POST':
                        request_body = {'limit': 1000, 'offset': offset}
                        async with session.post(working_endpoint['url'], json=request_body) as response:
                            if not response.ok:
                                raise Exception(f"Search request failed: {response.status} {response.reason}")
                            threads = await response.json()
                    else:
                        url = f"{working_endpoint['url'].split('?')[0]}?limit=1000&offset={offset}" if offset > 0 else working_endpoint['url']
                        async with session.get(url) as response:
                            if not response.ok:
                                raise Exception(f"Search request failed: {response.status} {response.reason}")
                            threads = await response.json()

                    if not threads or len(threads) == 0:
                        has_more = False
                    else:
                        all_threads.extend(threads)
                        offset += len(threads)
                        print(f"Found: {len(all_threads)} threads", end='\r')

            if len(all_threads) == 0:
                print('\n📋 No threads found.')
                return

            # Categorize threads
            categories = self.categorize_threads(all_threads)
            self.display_categories(categories)

            # Let user select what to delete (always pass fresh categories)
            threads_to_delete = await self.select_threads_to_delete(categories, all_threads)

            # Delete selected threads
            total_deleted = await self.delete_threads(threads_to_delete)

            if total_deleted > 0:
                print(f'\n🎉 Cleanup completed. Total threads deleted: {total_deleted}')
            else:
                print('\n✅ No threads were deleted.')

        except Exception as error:
            print(f'❌ Fatal error during cleanup: {error}')
            sys.exit(1)


def show_usage():
    """Show usage information"""
    usage = """
🧹 LangGraph Thread Cleanup Tool

Usage: python delete.py --url <BASE_URL> [--api-key <API_KEY>]

Required:
  --url, -u          Base URL of your LangGraph server
                     Example: --url http://localhost:9123

Optional:
  --api-key, -k      LangSmith API key (required for custom server endpoints)
                     Example: --api-key lsv2_pt_your_key_here

  --help, -h         Show this help message

Examples:
  python delete.py --url http://localhost:9123
  python delete.py --url https://my-server.com --api-key lsv2_pt_abc123
"""
    print(usage)


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--help', '-h', action='store_true', help='Show help message')
    parser.add_argument('--url', '-u', type=str, help='Base URL of your LangGraph server')
    parser.add_argument('--api-key', '-k', type=str, help='LangSmith API key')

    args = parser.parse_args()

    if args.help:
        show_usage()
        sys.exit(0)

    return args


def validate_config(args):
    """Validate configuration"""
    if not args.url:
        print('❌ Error: BASE_URL is required')
        print('')
        print('You must specify the URL of your LangGraph server:')
        print('  python delete.py --url http://localhost:9123')
        print('')
        print('For custom server endpoints, you may also need an API key:')
        print('  python delete.py --url https://my-server.com --api-key lsv2_pt_your_key')
        print('')
        print('Run with --help for more information')
        sys.exit(1)

    # Validate URL format
    try:
        result = urlparse(args.url)
        if not result.scheme or not result.netloc:
            raise ValueError("Invalid URL")
    except Exception:
        print('❌ Error: Invalid BASE_URL format')
        print(f'Provided: {args.url}')
        print('Expected format: http://localhost:9123 or https://my-server.com')
        sys.exit(1)

    # Validate API key format if provided
    if args.api_key and not args.api_key.startswith('lsv2_'):
        print('❌ Warning: API key should start with "lsv2_"')
        print(f'Provided: {args.api_key[:10]}...')
        print('LangSmith API keys typically start with "lsv2_pt_" or "lsv2_sk_"')
        print('')

    return args


async def main():
    """Main function"""
    try:
        args = parse_args()
        config = validate_config(args)

        cleanup = ThreadCleanup(config.url, config.api_key)
        await cleanup.interactive_clean()

    except KeyboardInterrupt:
        print('\n\n❌ Operation cancelled by user')
        sys.exit(0)
    except Exception as error:
        print(f'❌ Unhandled error: {error}')
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())