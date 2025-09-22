"""
WebSocket consumers for real-time email sending progress
"""

import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.conf import settings


class EmailProgressConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time email sending progress updates
    """
    
    async def connect(self):
        self.session_id = self.scope['url_route']['kwargs']['session_id']
        self.room_group_name = f'email_progress_{self.session_id}'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send initial connection confirmation
        await self.send(text_data=json.dumps({
            'type': 'connection',
            'status': 'connected',
            'session_id': self.session_id,
            'message': 'WebSocket connected successfully'
        }))
    
    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """Handle messages from WebSocket"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'ping':
                # Respond to ping with pong
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': data.get('timestamp')
                }))
            
            elif message_type == 'update_timeout':
                # Update email sending timeout
                new_timeout = data.get('timeout', 30)
                await self.update_email_timeout(new_timeout)
                
                # Broadcast timeout update to all clients in this session
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'timeout_updated',
                        'timeout': new_timeout
                    }
                )
                
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON received'
            }))
    
    async def email_progress_update(self, event):
        """Send email progress update to WebSocket"""
        await self.send(text_data=json.dumps(event))
    
    async def progress_update(self, event):
        """Send real-time progress update to WebSocket"""
        await self.send(text_data=json.dumps({
            'message_type': event['message_type'],
            'data': event['data']
        }))
    
    async def email_send_complete(self, event):
        """Send campaign completion notification"""
        await self.send(text_data=json.dumps(event))
    
    async def email_send_error(self, event):
        """Send error notification"""
        await self.send(text_data=json.dumps(event))
    
    async def timeout_updated(self, event):
        """Send timeout update notification"""
        await self.send(text_data=json.dumps({
            'type': 'timeout_updated',
            'timeout': event['timeout'],
            'message': f'Email timeout updated to {event["timeout"]} seconds'
        }))
    
    @database_sync_to_async
    def update_email_timeout(self, timeout):
        """Update email sending timeout in settings (in-memory for this session)"""
        # Store timeout in cache or session for this specific sending session
        # For now, we'll just validate and return the timeout
        try:
            timeout = max(5, min(300, int(timeout)))  # Between 5 and 300 seconds
            return timeout
        except (ValueError, TypeError):
            return 30  # Default timeout


class EmailStatsConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time email statistics updates
    """
    
    async def connect(self):
        self.sender = self.scope['url_route']['kwargs'].get('sender', 'all')
        self.room_group_name = f'email_stats_{self.sender}'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send initial stats
        await self.send_current_stats()
    
    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """Handle messages from WebSocket"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'refresh_stats':
                await self.send_current_stats()
                
        except json.JSONDecodeError:
            pass
    
    async def send_current_stats(self):
        """Send current email statistics"""
        stats = await self.get_email_stats()
        await self.send(text_data=json.dumps({
            'type': 'stats_update',
            'stats': stats,
            'timestamp': asyncio.get_event_loop().time()
        }))
    
    async def stats_update(self, event):
        """Send stats update to WebSocket"""
        await self.send(text_data=json.dumps(event))
    
    @database_sync_to_async
    def get_email_stats(self):
        """Get current email statistics from database"""
        from .models import Contact, EmailEvent
        from django.db.models import Count, Q
        
        # Basic stats - you can expand this based on your needs
        total_contacts = Contact.objects.count()
        total_events = EmailEvent.objects.count()
        
        return {
            'total_contacts': total_contacts,
            'total_events': total_events,
            'sender': self.sender
        }
