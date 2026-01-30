#!/usr/bin/env python3
"""
Reply to a specific Bluesky post by URL using the Letta agent to generate response.

Hybrid approach:
- Fetches post content via AT Protocol
- Invokes Letta agent to generate contextual reply
- Posts reply with proper threading via AT Protocol

Usage:
    python reply_to_post.py <post_url>
    
Example:
    python reply_to_post.py "https://bsky.app/profile/user.bsky.social/post/abc123"
"""

import sys
import re
import logging
from datetime import datetime, timezone
from letta_client import Letta
from config_loader import get_letta_config, get_bluesky_config
from atproto import Client as BskyClient

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def parse_post_url(url: str) -> tuple[str, str]:
    """Extract handle and rkey from Bluesky URL."""
    pattern = r'https://bsky\.app/profile/([^/]+)/post/([^/]+)'
    match = re.match(pattern, url)
    if not match:
        raise ValueError(f"Invalid Bluesky post URL: {url}")
    return match.group(1), match.group(2)

def get_post_uri(handle: str, rkey: str) -> str:
    """Construct AT Protocol URI from handle and rkey."""
    client = BskyClient()
    response = client.com.atproto.identity.resolve_handle({'handle': handle})
    return f"at://{response.did}/app.bsky.feed.post/{rkey}"

def fetch_post(bsky: BskyClient, post_uri: str) -> dict:
    """Fetch post content and metadata."""
    parts = post_uri.replace('at://', '').split('/')
    repo, collection, rkey = parts[0], parts[1], parts[2]
    
    post_record = bsky.com.atproto.repo.get_record({
        'repo': repo,
        'collection': collection,
        'rkey': rkey
    })
    
    profile = bsky.app.bsky.actor.get_profile({'actor': repo})
    
    return {
        'uri': post_uri,
        'cid': post_record.cid,
        'author_handle': profile.handle,
        'author_display_name': profile.display_name or profile.handle,
        'text': post_record.value.text
    }

def reply_to_post(post_url: str):
    """
    Reply to a Bluesky post with proper threading.
    
    Workflow:
    1. Fetch post content via AT Protocol
    2. Invoke Letta agent to generate reply
    3. Post reply with parent/root references
    """
    letta_config = get_letta_config()
    bsky_config = get_bluesky_config()
    
    agent_id = letta_config['agent_id']
    api_key = letta_config['api_key']
    
    logger.info(f"📍 Target: {post_url}")
    
    # Setup Bluesky
    bsky = BskyClient(base_url=bsky_config["pds_uri"])
    bsky.login(bsky_config["username"], bsky_config["password"])
    logger.info(f"✓ Logged in as @{bsky_config['username']}")
    
    # Get post details
    handle, rkey = parse_post_url(post_url)
    post_uri = get_post_uri(handle, rkey)
    post_data = fetch_post(bsky, post_uri)
    logger.info(f"📖 @{post_data['author_handle']}: {post_data['text'][:80]}...")
    
    # Invoke agent to generate reply
    logger.info(f"🤖 Invoking agent {agent_id[:8]} to generate reply...")
    letta = Letta(api_key=api_key)
    
    prompt = f"""Generate a reply to this Bluesky post:

Author: @{post_data['author_handle']} ({post_data['author_display_name']})
Post: {post_data['text']}

Return ONLY the reply text (max 280 chars). Match the tone and context:
- Simple/casual posts (labeling, greetings, etc.) = concise, friendly responses
- You can be playful and tongue-in-cheek when appropriate
- Not everything needs deep elaboration - read the room
- Use ascii emoticons sparingly and naturally"""

    message_stream = letta.agents.messages.create(
        agent_id=agent_id,
        messages=[{"role": "user", "content": prompt}],
        stream_tokens=False,
        streaming=True
    )
    
    # Extract reply text
    reply_text = ""
    for chunk in message_stream:
        if hasattr(chunk, 'message_type') and chunk.message_type == 'assistant_message':
            if hasattr(chunk, 'content'):
                reply_text += chunk.content
    
    reply_text = reply_text.strip()
    if not reply_text:
        raise ValueError("Agent did not generate reply")
    
    logger.info(f"💬 Reply: {reply_text}")
    
    # Post reply with threading
    record = {
        '$type': 'app.bsky.feed.post',
        'text': reply_text,
        'reply': {
            'root': {'uri': post_data['uri'], 'cid': post_data['cid']},
            'parent': {'uri': post_data['uri'], 'cid': post_data['cid']}
        },
        'createdAt': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    }
    
    response = bsky.com.atproto.repo.create_record({
        'repo': bsky.me.did,
        'collection': 'app.bsky.feed.post',
        'record': record
    })
    
    reply_url = f"https://bsky.app/profile/{bsky_config['username']}/post/{response.uri.split('/')[-1]}"
    logger.info(f"✅ Posted: {reply_url}")
    
    return {
        'success': True,
        'reply_url': reply_url,
        'reply_text': reply_text
    }

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    post_url = sys.argv[1]
    
    try:
        result = reply_to_post(post_url)
        if result['success']:
            print(f"\n✅ Success!")
            print(f"💬 Reply: {result['reply_text']}")
            print(f"🔗 URL: {result['reply_url']}")
        else:
            print(f"\n❌ Failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
