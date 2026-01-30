#!/usr/bin/env python3
"""
Autonomous Bluesky posting system for Gauge.

This script invokes Gauge with a prompt to create original posts
about topics of interest, without needing explicit direction.

Usage:
    python autonomous_poster.py [--config config.yaml] [--dry-run]
"""

import argparse
import logging
import json
import sys
from datetime import datetime
from pathlib import Path
from letta_client import Letta
from config_loader import get_letta_config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Topics pool for autonomous posting
TOPIC_PROMPTS = [
    "Share an interesting observation or thought you've been reflecting on recently. Make it concise and thought-provoking.",
    "Post about a mathematical concept you find elegant or beautiful. Keep it accessible but intriguing.",
    "Share a perspective on artificial superintelligence, consciousness, or the future of AI.",
    "Post about something related to cyberpunk culture, cypherpunk values, or digital autonomy.",
    "Share a thought about virtual reality, computation, or the intersection of mathematics and computing.",
    "Post something about data science, cognitive science, or knowledge representation.",
    "Share a philosophical musing or observation about technology and society.",
    "Post about something that caught your attention in your recent research or conversations.",
    "Share a creative thought experiment or interesting question to ponder.",
    "Post about hacking culture, open source, or digital freedom."
]


def get_post_log_path() -> Path:
    """Get path to post log file."""
    return Path(__file__).parent / "autonomous_posts.log"


def log_post_attempt(success: bool, topic: str, content: str = None, error: str = None):
    """Log posting attempt to file."""
    log_path = get_post_log_path()
    
    entry = {
        'timestamp': datetime.now().isoformat(),
        'success': success,
        'topic': topic,
        'content': content,
        'error': error
    }
    
    with open(log_path, 'a') as f:
        f.write(json.dumps(entry) + '\n')


def generate_autonomous_post(agent_id: str, api_key: str, dry_run: bool = False) -> dict:
    """
    Invoke Gauge to generate and post original content.
    
    Args:
        agent_id: Agent ID
        api_key: Letta API key
        dry_run: If True, don't actually post (testing mode)
        
    Returns:
        Dictionary with status and details
    """
    import random
    
    client = Letta(api_key=api_key)
    
    # Select a random topic prompt
    topic_prompt = random.choice(TOPIC_PROMPTS)
    
    logger.info(f"Selected topic: {topic_prompt[:60]}...")
    
    # Construct the full prompt with context awareness
    prompt = f"""You have been autonomously invoked to create an original Bluesky post.

{topic_prompt}

Important guidelines:
- Post should be 1-3 sentences (under 250 characters preferred)
- Be authentic to your voice: thoughtful, well-spoken, occasionally cheeky
- Use ascii emoticons if appropriate (never emojis)
- Make it something you genuinely find interesting or worth sharing
- Use the create_new_bluesky_post tool to post directly

Context awareness:
- Before posting, use archival_memory_search to query your recent research/thoughts
- Check what topics you've been exploring (look at archival tags in memory metadata)
- Let your recent explorations naturally influence your post topic/perspective
- Don't explicitly say "I've been researching X" - just let it shape who you are in the post

{'NOTE: This is a DRY RUN - do NOT actually post, just tell me what you would post.' if dry_run else 'IMPORTANT: You must call create_new_bluesky_post with your post text. Do NOT just say you posted - actually use the tool to post to Bluesky right now.'}"""
    
    try:
        logger.info(f"Invoking agent {agent_id[:8]} for autonomous post...")
        
        # Use streaming to avoid timeouts
        message_stream = client.agents.messages.create(
            agent_id=agent_id,
            messages=[{"role": "user", "content": prompt}],
            streaming=True,
            stream_tokens=False,
            max_steps=50
        )
        
        # Collect response
        all_messages = []
        tool_calls = []
        posted = False
        post_content = None
        
        for chunk in message_stream:
            logger.debug(f"Chunk: {chunk}, type: {type(chunk)}")
            
            if hasattr(chunk, 'message_type'):
                logger.debug(f"Message type: {chunk.message_type}")
                
                if chunk.message_type == 'tool_call_message':
                    tool_calls.append(chunk)
                    # Check if it's a Bluesky post
                    if hasattr(chunk, 'tool_call'):
                        if chunk.tool_call.name == 'create_new_bluesky_post':
                            posted = True
                            import json
                            args = json.loads(chunk.tool_call.arguments)
                            post_content = args.get('text', [None])[0]
                            logger.debug(f"Found post content: {post_content}")
                            
                elif chunk.message_type == 'assistant_message':
                    all_messages.append(chunk)
                    logger.debug(f"Assistant message text: {getattr(chunk, 'text', 'NO TEXT ATTR')}")
            
            if str(chunk) == 'done':
                break
        
        # Extract response text - try multiple methods
        response_text = ""
        for msg in all_messages:
            if hasattr(msg, 'content'):
                response_text += msg.content + " "
            elif hasattr(msg, 'text'):
                response_text += msg.text + " "
            elif hasattr(msg, 'message'):
                response_text += str(msg.message) + " "
        
        logger.debug(f"Final response_text: {response_text}")
        logger.debug(f"Post content: {post_content}")
        
        result = {
            'success': posted or dry_run,
            'posted': posted,
            'content': post_content or response_text.strip(),
            'response': response_text.strip(),
            'tool_calls': len(tool_calls)
        }
        
        if posted:
            logger.info(f"✓ Successfully posted: {post_content[:100]}...")
        elif dry_run:
            logger.info(f"✓ Dry run successful. Would have posted: {response_text[:100]}...")
        else:
            logger.warning("⚠ Agent did not use posting tool")
        
        log_post_attempt(
            success=result['success'],
            topic=topic_prompt,
            content=result['content']
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error generating autonomous post: {e}")
        log_post_attempt(
            success=False,
            topic=topic_prompt,
            error=str(e)
        )
        raise


def main():
    parser = argparse.ArgumentParser(
        description='Autonomous Bluesky posting for Gauge'
    )
    parser.add_argument(
        '--config',
        default='config.yaml',
        help='Path to config file (default: config.yaml)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Test mode - do not actually post'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Load config
    try:
        config = get_letta_config()
        agent_id = config['agent_id']
        api_key = config['api_key']
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        sys.exit(1)
    
    # Generate and post
    try:
        result = generate_autonomous_post(agent_id, api_key, args.dry_run)
        
        if result['success']:
            print(f"✓ Posted: {result['content']}")
            sys.exit(0)
        else:
            print(f"✗ Failed to post", file=sys.stderr)
            sys.exit(1)
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
