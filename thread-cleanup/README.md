# Thread Cleanup Tool

Interactive cleanup utility for managing LangGraph threads across deployments. Provides safe, categorized deletion with preview options.

## Prerequisites

- Python 3.7+
- `aiohttp` library

## Installation

Install required dependency:
```bash
pip install aiohttp
```

## Usage

### Basic Command
```bash
python3 delete.py --url YOUR_LANGGRAPH_URL --api-key YOUR_LANGSMITH_API_KEY
```

### Example
```bash
python3 delete.py \
  --url https://your-deployment.us.langgraph.app \
  --api-key your_langsmith_api_key_here
```

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--url` | Yes | Your LangGraph deployment URL |
| `--api-key` | Yes | Your LangSmith API key with appropriate permissions |
| `--help` | No | Show help message and exit |

## Features

### Interactive Menu
The script provides 7 deletion options:

1. **Delete by TIME** - Remove threads based on age
2. **Delete by STATUS** - Remove threads by their current status
3. **Delete by RUNS COUNT** - Remove threads based on execution count
4. **Delete by GRAPH ID** - Remove threads from specific graphs
5. **PREVIEW all threads** - View all threads without deleting
6. **Delete ALL threads** - Remove everything (use with caution!)
7. **Exit** - Quit without making changes

### Time-Based Deletion
- Within the last hour
- Within the last day
- Within the last week
- Within the last month
- All time (everything)
- Custom date (before a specific date)

### Status-Based Deletion
Remove threads by their execution status (idle, running, error, success, etc.)

### Runs Count Deletion
Remove threads based on how many times they've been executed (0 runs, 1 run, etc.)

### Graph ID Deletion
Remove threads from specific graph deployments

### Preview Mode
Every category includes a preview option to see exactly what will be deleted before confirming.

## Safety Features

- **Preview before delete**: Always see what will be removed
- **Confirmation prompts**: Multiple confirmations for destructive operations
- **Graceful navigation**: Easy back/cancel options at every step
- **Error handling**: Robust error handling with clear messages
- **Thread counts**: Always shows how many threads will be affected

## API Permissions

Your API key must have permissions to:
- List/search threads on your LangGraph deployment
- Delete threads from your LangGraph deployment

## Troubleshooting

### "Invalid tenant ID" Error
- Verify your API key has access to the specified deployment
- Check that the URL matches your actual LangGraph deployment
- Ensure the API key belongs to the correct organization/tenant

### "None of the thread endpoints worked"
- Confirm your LangGraph server is running and accessible
- Verify the URL format is correct
- Check API key permissions
- Ensure network connectivity to the deployment

### Connection Issues
- Verify the deployment URL is reachable
- Check for any firewall or network restrictions
- Confirm the API key is valid and not expired

## Example Session

```
Discovering threads...
Connecting to: https://your-deployment.us.langgraph.app
Found working endpoint: POST /threads/search
Found: 15 threads

Total threads found: 15

By Status:
├─ idle: 10
├─ success: 3
├─ error: 2

What would you like to delete?
1. Delete by TIME
2. Delete by STATUS
3. Delete by RUNS COUNT
4. Delete by GRAPH ID
5. PREVIEW all threads
6. Delete ALL threads - DANGEROUS!
7. Exit without deleting

Select option (1-7): 2

Delete by STATUS
1. idle (10 threads)
2. success (3 threads)
3. error (2 threads)
4. Review all status categories
5. Back to main menu

Select option (1-5): 1

You're about to delete 10 idle threads. This cannot be undone!
Do you want to continue? (yes/no): yes

Successfully deleted 10 threads
```

## Support

For issues or questions about this tool, please check:
1. Your API key permissions
2. LangGraph deployment accessibility
3. Network connectivity
4. API key expiration status