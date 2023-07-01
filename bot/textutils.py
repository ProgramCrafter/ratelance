import secrets


def part_escape_html(text):
    return text.replace('<', '&lt;').replace('>', '&gt;')


class JobPostUtils:
    @staticmethod
    def parse_amount_title_description(message):
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
        
        amount = float(price) * 1e9
        text = ' '.join(words[1:])
        
        if '.' in text:
            title, description = text.split('.', 1)
            return amount, title.strip(), description.strip()
        else:
            return amount, 'Untitled', text.strip()
    
    @staticmethod
    def format_article_list(message, my_address):
        try:
            amount, title, description = JobPostUtils.parse_amount_title_description(message)
            
            article_text = f'''
<b>{part_escape_html(title)}</b>
worth {amount/1e9:.2f} TON, by <pre>{my_address}</pre>

{part_escape_html(description)}
Job address: <a href="ton://transfer/invalid-address.a.ton">not deployed yet</a>
            '''.strip()
            
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
