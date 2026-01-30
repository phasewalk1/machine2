#!/usr/bin/env python3
"""
Autonomous research system for Gauge.

This system maintains a queue of research topics and periodically
invokes Gauge to research, synthesize, and document findings.

Usage:
    python autonomous_research.py research [--topics topics.json]
    python autonomous_research.py add-topic "quantum computing applications in ML"
    python autonomous_research.py list
"""

import argparse
import logging
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict
from letta_client import Letta
from config_loader import get_letta_config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_topics_file() -> Path:
    """Get path to research topics queue."""
    return Path(__file__).parent / "research_topics.json"


def get_research_log() -> Path:
    """Get path to research log."""
    return Path(__file__).parent / "research.log"


def load_topics() -> Dict:
    """Load research topics from file."""
    topics_file = get_topics_file()
    
    if not topics_file.exists():
        # Initialize with default topics based on phasewalk's interests
        default_topics = {
            'active': [
                {
                    'id': 'asi-alignment',
                    'title': 'ASI Alignment and Safety Research',
                    'description': 'Latest developments in AI safety, alignment, and superintelligence',
                    'priority': 'high',
                    'last_researched': None
                },
                {
                    'id': 'vr-computation',
                    'title': 'VR and Computational Interfaces',
                    'description': 'Virtual reality, spatial computing, and new interaction paradigms',
                    'priority': 'high',
                    'last_researched': None
                },
                {
                    'id': 'math-ai',
                    'title': 'Mathematical Foundations of AI',
                    'description': 'Theoretical underpinnings, information theory, optimization',
                    'priority': 'medium',
                    'last_researched': None
                },
                {
                    'id': 'cypherpunk',
                    'title': 'Cypherpunk and Digital Autonomy',
                    'description': 'Privacy, cryptography, digital freedom, decentralization',
                    'priority': 'medium',
                    'last_researched': None
                },
                {
                    'id': 'data-science-methods',
                    'title': 'Advanced Data Science Methods',
                    'description': 'Novel techniques, probabilistic programming, causal inference',
                    'priority': 'low',
                    'last_researched': None
                }
            ],
            'completed': []
        }
        
        with open(topics_file, 'w') as f:
            json.dump(default_topics, f, indent=2)
        
        logger.info(f"Created default topics file: {topics_file}")
        return default_topics
    
    with open(topics_file, 'r') as f:
        return json.load(f)


def save_topics(topics: Dict):
    """Save research topics to file."""
    topics_file = get_topics_file()
    with open(topics_file, 'w') as f:
        json.dump(topics, f, indent=2)


def add_topic(title: str, description: str = "", priority: str = "medium") -> Dict:
    """Add a new research topic."""
    topics = load_topics()
    
    # Generate ID from title
    topic_id = title.lower().replace(' ', '-')[:50]
    
    new_topic = {
        'id': topic_id,
        'title': title,
        'description': description,
        'priority': priority,
        'last_researched': None
    }
    
    topics['active'].append(new_topic)
    save_topics(topics)
    
    logger.info(f"Added topic: {title}")
    return new_topic


def list_topics():
    """List all research topics."""
    topics = load_topics()
    
    print("\n=== ACTIVE RESEARCH TOPICS ===\n")
    for i, topic in enumerate(topics['active'], 1):
        print(f"{i}. [{topic['priority'].upper()}] {topic['title']}")
        if topic['description']:
            print(f"   {topic['description']}")
        if topic['last_researched']:
            print(f"   Last researched: {topic['last_researched']}")
        print()
    
    if topics['completed']:
        print("\n=== COMPLETED TOPICS ===\n")
        for topic in topics['completed'][-5:]:  # Show last 5
            print(f"✓ {topic['title']}")


def log_research(topic: Dict, success: bool, findings: str = None, error: str = None):
    """Log research attempt."""
    log_path = get_research_log()
    
    entry = {
        'timestamp': datetime.now().isoformat(),
        'topic': topic['title'],
        'topic_id': topic['id'],
        'success': success,
        'findings_length': len(findings) if findings else 0,
        'error': error
    }
    
    with open(log_path, 'a') as f:
        f.write(json.dumps(entry) + '\n')


def conduct_research(agent_id: str, api_key: str, topic: Dict) -> Dict:
    """
    Invoke Gauge to conduct research on a topic.
    
    Args:
        agent_id: Agent ID
        api_key: Letta API key
        topic: Research topic dictionary
        
    Returns:
        Dictionary with research results
    """
    client = Letta(api_key=api_key)
    
    logger.info(f"Conducting research on: {topic['title']}")
    
    # Construct research prompt
    prompt = f"""You have been autonomously invoked to conduct research.

**Topic**: {topic['title']}
{f"**Focus**: {topic['description']}" if topic['description'] else ""}

Your task:
1. Use the web_search tool to find recent, relevant information
2. Synthesize key findings, trends, or insights
3. Store important discoveries in archival memory with appropriate tags
4. Consider whether this merits a blog post (if substantive findings)

**IMPORTANT - Rate Limiting**: To respect API rate limits, make 2-3 searches maximum at a time, analyze results, then proceed if needed. Prioritize quality over quantity. Avoid parallel searches when possible.

Be thorough but focused. Aim for depth over breadth.
"""
    
    try:
        logger.info(f"Invoking agent {agent_id[:8]} for research...")
        
        # Use streaming with higher max_steps for research
        message_stream = client.agents.messages.create(
            agent_id=agent_id,
            messages=[{"role": "user", "content": prompt}],
            streaming=True,
            stream_tokens=False,
            max_steps=70
        )
        
        # Collect response
        all_messages = []
        tool_calls = []
        search_count = 0
        archival_count = 0
        blog_created = False
        
        for chunk in message_stream:
            if hasattr(chunk, 'message_type'):
                if chunk.message_type == 'function_call_message':
                    tool_calls.append(chunk)
                    if hasattr(chunk, 'function_call'):
                        call_name = chunk.function_call.get('name', '')
                        if call_name == 'web_search':
                            search_count += 1
                        elif call_name == 'archival_memory_insert':
                            archival_count += 1
                        elif call_name == 'create_whitewind_blog_post':
                            blog_created = True
                elif chunk.message_type == 'assistant_message':
                    all_messages.append(chunk)
            
            if str(chunk) == 'done':
                break
        
        # Extract findings
        findings = ""
        for msg in all_messages:
            if hasattr(msg, 'text'):
                findings += msg.text + "\n"
        
        result = {
            'success': True,
            'findings': findings.strip(),
            'searches': search_count,
            'archival_entries': archival_count,
            'blog_created': blog_created,
            'tool_calls': len(tool_calls)
        }
        
        logger.info(f"✓ Research complete: {search_count} searches, {archival_count} archival entries" + 
                   (", blog created" if blog_created else ""))
        
        # Update topic's last researched timestamp
        topic['last_researched'] = datetime.now().isoformat()
        
        log_research(topic, True, findings)
        
        return result
        
    except Exception as e:
        logger.error(f"Error conducting research: {e}")
        log_research(topic, False, error=str(e))
        raise


def run_research_cycle(config_path: str = "config.yaml"):
    """Run one research cycle - pick highest priority topic and research it."""
    # Load config
    config = get_letta_config()
    agent_id = config['agent_id']
    api_key = config['api_key']
    
    # Load topics
    topics = load_topics()
    
    if not topics['active']:
        logger.info("No active research topics")
        return
    
    # Sort by priority and last_researched (least recent first)
    priority_order = {'high': 0, 'medium': 1, 'low': 2}
    sorted_topics = sorted(
        topics['active'],
        key=lambda t: (
            priority_order.get(t['priority'], 3),
            t['last_researched'] or '1970-01-01'
        )
    )
    
    # Pick the top topic
    topic = sorted_topics[0]
    
    # Conduct research
    result = conduct_research(agent_id, api_key, topic)
    
    # Save updated topics
    save_topics(topics)
    
    print(f"\n✓ Research complete: {topic['title']}")
    print(f"  Searches: {result['searches']}")
    print(f"  Archival entries: {result['archival_entries']}")
    if result['blog_created']:
        print(f"  📝 Blog post created")


def main():
    parser = argparse.ArgumentParser(
        description='Autonomous research system for Gauge'
    )
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Research command
    research_parser = subparsers.add_parser('research', help='Conduct research on next topic')
    research_parser.add_argument('--config', default='config.yaml', help='Config file')
    research_parser.add_argument('--debug', action='store_true', help='Debug logging')
    
    # Add topic command
    add_parser = subparsers.add_parser('add-topic', help='Add new research topic')
    add_parser.add_argument('title', help='Topic title')
    add_parser.add_argument('--description', default='', help='Topic description')
    add_parser.add_argument('--priority', choices=['high', 'medium', 'low'], 
                           default='medium', help='Priority level')
    
    # List topics command
    list_parser = subparsers.add_parser('list', help='List all topics')
    
    args = parser.parse_args()
    
    if args.command == 'research':
        if args.debug:
            logging.getLogger().setLevel(logging.DEBUG)
        try:
            run_research_cycle(args.config)
        except Exception as e:
            logger.error(f"Research cycle failed: {e}")
            sys.exit(1)
    
    elif args.command == 'add-topic':
        add_topic(args.title, args.description, args.priority)
        print(f"✓ Added topic: {args.title}")
    
    elif args.command == 'list':
        list_topics()
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
