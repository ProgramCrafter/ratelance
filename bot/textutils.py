from cli.jobs import analytic_msg, job_state_init, JOB_NOTIFICATIONS
from cli.bcutils import encode_text
from tonsdk.utils import Address
from tonsdk.boc import Cell

from base64 import urlsafe_b64encode, b16encode
import secrets


def part_escape_html(text: str) -> str:
    return text.replace('<', '&lt;').replace('>', '&gt;')


def ton_link(destination: Address, init: Cell, body: Cell, value: int) -> str:
    addr = destination.to_string(True, True, True)
    boc  = urlsafe_b64encode(body.to_boc(False)).decode('ascii')
    link = f'ton://transfer/{addr}?bin={boc}&amount={value}'
    if init:
        link += '&init='
        link += urlsafe_b64encode(init.to_boc(False)).decode('ascii')
    return link


class JobPostUtils:
    @staticmethod
    def parse_amount_title_description(message: str) -> tuple[int, str, str]:
        # message is like '20 [ton] the job. text'
        #              or '20ton    the job. text'
        
        words = message.strip().split(' ', 2)
        if len(words) < 2: raise Exception('insufficient words')
        
        price = words[0].lower()
        if price.endswith('ton'):
            price = price.removesuffix('ton')
        elif words[1].lower() == 'ton':         # removing TON suffix
            words.pop(1)
        
        if '$' in price: raise Exception('$ denomination is not supported')
        
        amount = int(float(price) * 1e9)
        if amount < 10**8: raise Exception('too small job price')
        
        text = ' '.join(words[1:])
        
        if '.' in text:
            title, description = text.split('.', 1)
            return amount, title.strip(), description.strip()
        else:
            return amount, 'Untitled', text.strip()
    
    @staticmethod
    def create_address_deploylinks(value: int, text: str, my_address: str,
                                   public_key: bytes) -> tuple[str, list[str]]:
        description_cell = encode_text(text)
        key_int = int.from_bytes(public_key, 'big')
        
        state_init = job_state_init(my_address, value, description_cell, key_int)
        addr = Address('0:' + b16encode(state_init.bytes_hash()).decode('ascii'))
        am = analytic_msg(addr, value, description_cell, key_int)
        
        jobs = Address(JOB_NOTIFICATIONS)
        jobs.is_bounceable = False
        
        return addr.to_string(True, True, True), [
                ton_link(addr, state_init, Cell(), value),
                ton_link(jobs, None, am, 5*10**7)
            ]
    
    @staticmethod
    def format_article_list(message: str, my_address: str, public_key: bytes) -> list:
        try:
            amount, title, description = JobPostUtils.parse_amount_title_description(message)
            
            job_text = f'# {title}\n\n{description}'
            job_addr, _ = JobPostUtils.create_address_deploylinks(amount, job_text, my_address, public_key)
            
            article_text = f'''
            <b>{part_escape_html(title)}</b>
            worth {amount/1e9:.2f} TON, by <pre>{my_address}</pre>
            
            {part_escape_html(description)}
            
            <b>Job address:</b> <pre>{job_addr}</pre>
            '''.replace(' ' * 12, '').strip()
            
            return [{
                'type': 'article',
                'id': secrets.token_urlsafe(),
                'title': f'Create job "{part_escape_html(title)}" worth {amount/1e9:.2f} TON',
                'input_message_content': {
                    'message_text': article_text, 'parse_mode': 'html'
                }
            }]
        except:
            return []
    
    @staticmethod
    def format_deploy_links(message: str, my_address: str, public_key: bytes) -> str:
        try:
            amount, title, description = JobPostUtils.parse_amount_title_description(message)
            
            job_text = f'# {title}\n\n{description}'
            _, links = JobPostUtils.create_address_deploylinks(amount, job_text, my_address, public_key)
            
            deploy, notify = links
            
            return (f'<b>Job "{part_escape_html(title)}" worth {amount/1e9:.2f} TON</b>\n' + 
                    f'<a href="{deploy}">[Deploy]</a> + ' + 
                    f'<a href="{notify}">[notify others about job contract]</a>')
        except Exception as e:
            return 'Error when creating deploy links: ' + repr(e)
