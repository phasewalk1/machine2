#!/usr/bin/env python3
"""
Programmatically invoke Gauge (the agent) with a message.

Usage:
    python invoke_gauge.py "What are your thoughts on ASI?"
    echo "Research quantum computing" | python invoke_gauge.py
"""

import sys
import argparse
import logging
from letta_client import Letta
from config_loader import load_config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def invoke_agent(prompt: str, agent_id: str, api_key: str, max_steps: int = 100) -> dict:
    """
    Send a message to the agent and return the full response.
    
    Args:
        prompt: The message to send
        agent_id: Agent ID
        api_key: Letta API key
        max_steps: Maximum steps for agent execution
        
    Returns:
        Dictionary with:
            - messages: All messages from the agent
            - tool_calls: Any tool calls made
            - reasoning: Reasoning steps (if any)
    """
    client = Letta(api_key=api_key)
    
    logger.info(f"Invoking agent {agent_id[:8]}...")
    logger.debug(f"Prompt: {prompt[:100]}...")
    
    try:
        # Use streaming to avoid timeouts
        message_stream = client.agents.messages.create(
            agent_id=agent_id,
            messages=[{"role": "user", "content": prompt}],
            streaming=True,
            stream_tokens=False,
            max_steps=max_steps
        )
        
        # Collect response
        all_messages = []
        tool_calls = []
        reasoning = []
        
        for chunk in message_stream:
            if hasattr(chunk, 'message_type'):
                if chunk.message_type == 'reasoning_message':
                    reasoning.append(chunk)
                elif chunk.message_type == 'function_call_message':
                    tool_calls.append(chunk)
                elif chunk.message_type in ['assistant_message', 'function_return']:
                    all_messages.append(chunk)
            
            if str(chunk) == 'done':
                break
        
        logger.info(f"Response received: {len(all_messages)} messages, {len(tool_calls)} tool calls")
        
        return {
            'messages': all_messages,
            'tool_calls': tool_calls,
            'reasoning': reasoning
        }
        
    except Exception as e:
        logger.error(f"Error invoking agent: {e}")
        raise


def extract_text_response(response: dict) -> str:
    """Extract the text content from agent response messages."""
    text_parts = []
    
    for msg in response.get('messages', []):
        if hasattr(msg, 'message_type') and msg.message_type == 'assistant_message':
            if hasattr(msg, 'text'):
                text_parts.append(msg.text)
            elif hasattr(msg, 'content'):
                text_parts.append(msg.content)
    
    return '\n'.join(text_parts)


def main():
    parser = argparse.ArgumentParser(
        description='Programmatically invoke Gauge with a message'
    )
    parser.add_argument(
        'prompt',
        nargs='?',
        help='The prompt to send (if not provided, reads from stdin)'
    )
    parser.add_argument(
        '--config',
        default='config.yaml',
        help='Path to config file (default: config.yaml)'
    )
    parser.add_argument(
        '--max-steps',
        type=int,
        default=100,
        help='Maximum agent steps (default: 100)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    parser.add_argument(
        '--full',
        action='store_true',
        help='Print full response including tool calls'
    )
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Get prompt
    if args.prompt:
        prompt = args.prompt
    elif not sys.stdin.isatty():
        prompt = sys.stdin.read().strip()
    else:
        print("Error: No prompt provided. Usage: invoke_gauge.py 'your message'", file=sys.stderr)
        sys.exit(1)
    
    if not prompt:
        print("Error: Empty prompt", file=sys.stderr)
        sys.exit(1)
    
    # Load config
    try:
        config = load_config(args.config)
        agent_id = config['letta']['agent_id']
        api_key = config['letta']['api_key']
    except Exception as e:
        print(f"Error loading config: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Invoke agent
    try:
        response = invoke_agent(prompt, agent_id, api_key, args.max_steps)
        
        if args.full:
            # Print full structured response
            print("\n=== MESSAGES ===")
            for msg in response['messages']:
                print(f"{msg.message_type}: {msg}")
            
            if response['tool_calls']:
                print("\n=== TOOL CALLS ===")
                for call in response['tool_calls']:
                    print(call)
            
            if response['reasoning']:
                print("\n=== REASONING ===")
                for r in response['reasoning']:
                    print(r)
        else:
            # Print just the text response
            text = extract_text_response(response)
            print(text)
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
