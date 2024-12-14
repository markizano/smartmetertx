'''
Handles the rough edges of AWS SNS notifications for modular use of notifications.
'''

import boto3
import traceback as tb
from kizano import getLogger, getConfig

log = getLogger(__name__)
sns = boto3.client('sns')

class NotifyHelper(object):
    def __init__(self):
        self.config = getConfig()
        if 'aws' in self.config and 'sns' in self.config['aws']:
            self.notify_topic = self.config['aws']['sns']['notify_topic']
            self.error_topic = self.config['aws']['sns']['error_topic']
        else:
            topics = sns.list_topics()
            if 'Topics' in topics:
                log.debug('Topics: %s' % topics['Topics'])
                # Set self.notify_topic to the config `.aws.sns.notify_topic` or a topic with "INFO" in the name if config not set.
                self.notify_topic = next((x['TopicArn'] for x in topics['Topics'] if 'INFO' in x['TopicArn'].upper()))
                # Same with `self.error_topic` but with "ERROR" in the name.
                self.error_topic = next((x['TopicArn'] for x in topics['Topics'] if 'ERROR' in x['TopicArn'].upper()))
            else:
                log.error('No topics found!')
                self.notify_topic = ''
                self.error_topic = ''

    def info(self, subject: str, message: str) -> None:
        '''
        Send an INFO message to the configured SNS topic.
        '''
        if self.notify_topic:
            sns.publish(
                TopicArn=self.notify_topic,
                Subject=subject,
                Message=message,
            )
        else:
            log.warning('No notify_topic set in config!')

    def error(self, subject: str, message: str) -> None:
        '''
        Send an ERROR message to the configured SNS topic.
        '''
        if self.error_topic:
            sns.publish(
                TopicArn=self.error_topic,
                Subject=subject,
                Message=f'{message}\nTraceback:\n{tb.format_exc()}',
            )
        else:
            log.warning('No error_topic set in config!')
