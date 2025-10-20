"""Platform Integrations for Discord, Zoom, and other meeting programs"""
import logging
import subprocess
import platform
from typing import Optional, Dict, List
from enum import Enum

log = logging.getLogger("Translator")

class Platform(Enum):
    """Supported platforms for integration"""
    DISCORD = "discord"
    ZOOM = "zoom"
    TEAMS = "teams"
    SLACK = "slack"
    GOOGLE_MEET = "google_meet"
    SKYPE = "skype"
    CUSTOM = "custom"

class PlatformIntegration:
    """Manages integrations with various meeting and communication platforms"""
    
    def __init__(self):
        self.enabled_platforms = set()
        self.platform_configs = {
            Platform.DISCORD: {
                'name': 'Discord',
                'description': 'Voice and text translation for Discord',
                'supports_voice': True,
                'supports_text': True,
                'requires_bot': False,
                'audio_capture': 'system'
            },
            Platform.ZOOM: {
                'name': 'Zoom',
                'description': 'Real-time translation for Zoom meetings',
                'supports_voice': True,
                'supports_text': True,
                'requires_bot': False,
                'audio_capture': 'system'
            },
            Platform.TEAMS: {
                'name': 'Microsoft Teams',
                'description': 'Translation for Teams meetings',
                'supports_voice': True,
                'supports_text': True,
                'requires_bot': False,
                'audio_capture': 'system'
            },
            Platform.SLACK: {
                'name': 'Slack',
                'description': 'Text translation for Slack channels',
                'supports_voice': False,
                'supports_text': True,
                'requires_bot': True,
                'audio_capture': None
            },
            Platform.GOOGLE_MEET: {
                'name': 'Google Meet',
                'description': 'Translation for Google Meet',
                'supports_voice': True,
                'supports_text': True,
                'requires_bot': False,
                'audio_capture': 'system'
            },
            Platform.SKYPE: {
                'name': 'Skype',
                'description': 'Translation for Skype calls',
                'supports_voice': True,
                'supports_text': True,
                'requires_bot': False,
                'audio_capture': 'system'
            }
        }
        
        self.virtual_audio_device = None
        self.detect_platform_availability()
    
    def detect_platform_availability(self):
        """Detect which platforms are currently available/running"""
        system = platform.system()
        
        # This is a basic implementation - in production, you'd want more sophisticated detection
        log.info("Scanning for running communication platforms...")
        
        # Platform-specific detection would go here
        # For now, we assume all platforms are potentially available
        log.info("Platform integration ready for: Discord, Zoom, Teams, Meet, Skype")
    
    def enable_platform(self, platform: Platform) -> bool:
        """
        Enable integration for a specific platform
        
        Args:
            platform: Platform enum value
        
        Returns:
            True if successful
        """
        if platform not in self.platform_configs:
            log.error(f"Unknown platform: {platform}")
            return False
        
        config = self.platform_configs[platform]
        
        # Check if voice duplication is needed
        if config['supports_voice']:
            log.info(f"Enabling voice integration for {config['name']}")
            # Setup audio routing if needed
            if config['audio_capture'] == 'system':
                self._setup_audio_routing(platform)
        
        self.enabled_platforms.add(platform)
        log.info(f"Enabled integration for {config['name']}")
        return True
    
    def disable_platform(self, platform: Platform) -> bool:
        """Disable integration for a specific platform"""
        if platform in self.enabled_platforms:
            self.enabled_platforms.remove(platform)
            log.info(f"Disabled integration for {self.platform_configs[platform]['name']}")
            return True
        return False
    
    def _setup_audio_routing(self, platform: Platform):
        """Setup virtual audio device routing for a platform"""
        system = platform.system()
        
        if system == "Windows":
            log.info("Windows: Use VB-Cable or Virtual Audio Cable for audio routing")
            # Guide user to setup virtual audio cable
        elif system == "Darwin":  # macOS
            log.info("macOS: Use BlackHole or Soundflower for audio routing")
            # Guide user to setup BlackHole
        elif system == "Linux":
            log.info("Linux: Use PulseAudio loopback for audio routing")
            # Setup PulseAudio loopback
    
    def is_platform_enabled(self, platform: Platform) -> bool:
        """Check if a platform integration is enabled"""
        return platform in self.enabled_platforms
    
    def get_enabled_platforms(self) -> List[Platform]:
        """Get list of enabled platforms"""
        return list(self.enabled_platforms)
    
    def get_platform_config(self, platform: Platform) -> Optional[Dict]:
        """Get configuration for a platform"""
        return self.platform_configs.get(platform)
    
    def get_all_platforms_info(self) -> Dict:
        """Get information about all supported platforms"""
        return {
            platform: {
                'enabled': platform in self.enabled_platforms,
                **config
            }
            for platform, config in self.platform_configs.items()
        }
    
    def setup_virtual_microphone(self) -> bool:
        """
        Setup virtual microphone for outputting translated audio
        
        Returns:
            True if successful
        """
        system = platform.system()
        
        try:
            if system == "Windows":
                log.info("Virtual microphone setup: Install VB-Audio Virtual Cable")
                log.info("Download from: https://vb-audio.com/Cable/")
                return True
            elif system == "Darwin":
                log.info("Virtual microphone setup: Install BlackHole")
                log.info("Run: brew install blackhole-2ch")
                return True
            elif system == "Linux":
                log.info("Virtual microphone setup: Using PulseAudio")
                # Create virtual sink
                subprocess.run([
                    "pactl", "load-module", "module-null-sink",
                    "sink_name=translator_output",
                    "sink_properties=device.description='Translator_Output'"
                ], check=False)
                return True
        except Exception as e:
            log.error(f"Failed to setup virtual microphone: {e}")
            return False
        
        return False
    
    def get_setup_instructions(self, platform: Platform) -> str:
        """Get setup instructions for a specific platform"""
        config = self.platform_configs.get(platform)
        if not config:
            return "Platform not supported"
        
        system_name = platform.system()
        instructions = f"# Setup Instructions for {config['name']}\n\n"
        
        if config['supports_voice']:
            instructions += "## Audio Setup\n"
            if system_name == "Windows":
                instructions += "1. Install VB-Audio Virtual Cable\n"
                instructions += "2. Set Virtual Cable as default output in Windows\n"
                instructions += "3. In the translator, select Virtual Cable as input\n"
                instructions += f"4. In {config['name']}, select Virtual Cable as microphone\n\n"
            elif system_name == "Darwin":
                instructions += "1. Install BlackHole: brew install blackhole-2ch\n"
                instructions += "2. Create Multi-Output Device in Audio MIDI Setup\n"
                instructions += "3. Select Multi-Output Device in System Preferences\n"
                instructions += f"4. In {config['name']}, select BlackHole as microphone\n\n"
            else:  # Linux
                instructions += "1. The translator will create a virtual audio device\n"
                instructions += f"2. In {config['name']}, select 'Translator_Output' as microphone\n\n"
        
        if config['supports_text']:
            instructions += "## Text Translation\n"
            instructions += "1. Enable text translation in the translator settings\n"
            instructions += "2. Use overlay mode to see translations in real-time\n"
            if config.get('requires_bot'):
                instructions += "3. Setup bot integration for automatic message translation\n"
        
        return instructions


# Global instance
platform_integration = PlatformIntegration()
