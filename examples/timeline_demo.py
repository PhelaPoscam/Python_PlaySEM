#!/usr/bin/env python3
"""
Timeline demo - demonstrates synchronized effect rendering.

This example shows how to create a timeline with multiple effects
and play them back with precise timing synchronization.
"""

import sys
import time
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.device_driver import (
    MockLightDevice,
    MockWindDevice,
    MockVibrationDevice
)
from src.device_manager import DeviceManager
from src.effect_dispatcher import EffectDispatcher
from src.effect_metadata import create_effect, create_timeline
from src.timeline import Timeline

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(name)s] - %(message)s',
    datefmt='%H:%M:%S.%f'
)


def create_mock_device_manager():
    """Create a device manager with mock devices."""
    # For demo, we'll use mock devices directly
    # In production, this would go through proper connectivity
    mock_client = type('MockClient', (), {
        'publish': lambda *args: None
    })()
    return DeviceManager(client=mock_client)


def demo_simple_timeline():
    """Demonstrate a simple timeline with sequential effects."""
    print("\n" + "=" * 60)
    print("DEMO 1: Simple Sequential Timeline")
    print("=" * 60)
    
    # Create components
    device_manager = create_mock_device_manager()
    dispatcher = EffectDispatcher(device_manager)
    scheduler = Timeline(dispatcher, tick_interval=0.01)
    
    # Create timeline with effects
    effect_timeline = create_timeline(
        create_effect('light', timestamp=0, duration=1000,
                     intensity=100),
        create_effect('wind', timestamp=500, duration=1000,
                     intensity=75),
        create_effect('vibration', timestamp=1000, duration=500,
                     intensity=50),
        title='Simple Scene'
    )
    
    print(f"\nTimeline: {effect_timeline.metadata['title']}")
    print(f"Total duration: {effect_timeline.total_duration}ms")
    print(f"Number of effects: {len(effect_timeline.effects)}\n")
    
    # Set up callbacks
    def on_effect(effect):
        print(f"  ▶ Effect executed: {effect.effect_type} "
              f"(intensity={effect.intensity})")
    
    def on_complete():
        print("\n✓ Timeline completed!\n")
    
    scheduler.set_callbacks(
        on_effect=on_effect,
        on_complete=on_complete
    )
    
    # Load and play timeline
    scheduler.load_timeline(effect_timeline)
    scheduler.start()
    
    # Monitor playback
    while scheduler.is_running:
        status = scheduler.get_status()
        pos_sec = status['current_position'] / 1000.0
        print(f"\rPosition: {pos_sec:.2f}s", end='', flush=True)
        time.sleep(0.1)
    
    print("\n")


def demo_synchronized_effects():
    """Demonstrate synchronized multi-sensory effects."""
    print("\n" + "=" * 60)
    print("DEMO 2: Synchronized Multi-Sensory Timeline")
    print("=" * 60)
    
    device_manager = create_mock_device_manager()
    dispatcher = EffectDispatcher(device_manager)
    scheduler = Timeline(dispatcher)
    
    # Create an action scene with synchronized effects
    effect_timeline = create_timeline(
        # Opening scene: bright light fade-in
        create_effect('light', timestamp=0, duration=2000,
                     intensity=80, parameters={'color': '#FFFFFF'}),
        
        # Wind starts building
        create_effect('wind', timestamp=1000, duration=3000,
                     intensity=60),
        
        # Thunder flash
        create_effect('light', timestamp=2000, duration=200,
                     intensity=100, parameters={'color': '#FFFFFF'}),
        create_effect('vibration', timestamp=2000, duration=200,
                     intensity=80),
        
        # Storm intensifies
        create_effect('wind', timestamp=3000, duration=2000,
                     intensity=90),
        create_effect('vibration', timestamp=3500, duration=1500,
                     intensity=60),
        
        # Calm after storm
        create_effect('light', timestamp=5000, duration=2000,
                     intensity=40, parameters={'color': '#8888FF'}),
        
        title='Thunder Storm Scene',
        duration=7000
    )
    
    print(f"\nTimeline: {effect_timeline.metadata['title']}")
    print(f"Total duration: {effect_timeline.total_duration}ms")
    print(f"Effects: {len(effect_timeline.effects)}\n")
    
    # Effect callback with details
    effect_count = [0]
    
    def on_effect(effect):
        effect_count[0] += 1
        print(f"  [{effect.timestamp}ms] {effect.effect_type.upper()}: "
              f"intensity={effect.intensity}")
    
    def on_complete():
        print(f"\n✓ Storm scene complete! "
              f"({effect_count[0]} effects executed)\n")
    
    scheduler.set_callbacks(
        on_effect=on_effect,
        on_complete=on_complete
    )
    
    # Play timeline
    scheduler.load_timeline(effect_timeline)
    scheduler.start()
    
    while scheduler.is_running:
        time.sleep(0.1)


def demo_pause_resume():
    """Demonstrate pause and resume functionality."""
    print("\n" + "=" * 60)
    print("DEMO 3: Pause and Resume Timeline")
    print("=" * 60)
    
    device_manager = create_mock_device_manager()
    dispatcher = EffectDispatcher(device_manager)
    scheduler = Timeline(dispatcher)
    
    effect_timeline = create_timeline(
        create_effect('light', timestamp=0, duration=4000, intensity=100),
        create_effect('wind', timestamp=1000, duration=3000, intensity=75),
        title='Pause Test'
    )
    
    print(f"\nTimeline: {effect_timeline.metadata['title']}")
    print("Starting playback...\n")
    
    scheduler.load_timeline(effect_timeline)
    scheduler.start()
    
    # Play for 1 second
    time.sleep(1.0)
    print("⏸  PAUSING at ~1000ms")
    scheduler.pause()
    
    # Pause for 1 second
    time.sleep(1.0)
    print("▶  RESUMING")
    scheduler.resume()
    
    # Let it finish
    while scheduler.is_running:
        time.sleep(0.1)
    
    print("✓ Timeline completed with pause/resume\n")


def demo_event_based():
    """Demonstrate event-based effect triggering."""
    print("\n" + "=" * 60)
    print("DEMO 4: Event-Based Effect Triggering")
    print("=" * 60)
    
    device_manager = create_mock_device_manager()
    dispatcher = EffectDispatcher(device_manager)
    scheduler = Timeline(dispatcher)
    
    # Create timeline for background effects
    background_timeline = create_timeline(
        create_effect('light', timestamp=0, duration=5000, intensity=40),
        title='Background'
    )
    
    print("\nBackground timeline running...")
    print("Triggering event-based effects at random times...\n")
    
    scheduler.load_timeline(background_timeline)
    scheduler.start()
    
    # Trigger event effects at specific moments
    events = [
        (500, 'vibration', 80, 'Button press'),
        (1200, 'wind', 60, 'Door opens'),
        (2500, 'light', 100, 'Flash'),
        (3500, 'vibration', 50, 'Notification')
    ]
    
    start_time = time.time()
    for event_time, effect_type, intensity, description in events:
        # Wait until event time
        while (time.time() - start_time) * 1000 < event_time:
            time.sleep(0.01)
        
        # Trigger event effect
        event_effect = create_effect(
            effect_type,
            timestamp=0,
            duration=200,
            intensity=intensity,
            event_id=hash(description)
        )
        print(f"  ⚡ Event: {description} "
              f"({effect_type}, intensity={intensity})")
        scheduler.add_event_effect(event_effect)
    
    # Wait for background to finish
    while scheduler.is_running:
        time.sleep(0.1)
    
    print("\n✓ Event-based demo completed\n")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("PythonPlaySEM Timeline Scheduler Demo")
    print("=" * 60)
    print("\nThis demo shows synchronized sensory effect rendering")
    print("with precise timing control.\n")
    print("Press Ctrl+C to skip remaining demos.\n")
    
    try:
        demo_simple_timeline()
        time.sleep(1.0)
        
        demo_synchronized_effects()
        time.sleep(1.0)
        
        demo_pause_resume()
        time.sleep(1.0)
        
        demo_event_based()
        
        print("=" * 60)
        print("All demos completed successfully!")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user.")
    except Exception as e:
        print(f"\n\nError during demo: {e}")
        raise
