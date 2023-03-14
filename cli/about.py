from .colors import nh, h, nb, b, ns, s

PROMPT_SINGLE = f'''{b}{"="*80}{ns}
Jobs       {h}jl{nh}: list {h}jp{nh}: post   {h}ji{nh}: info {h}jv{nh}: load+verify {h}jr{nh}: revoke {h}jd{nh}: delegate
Offers     {h}ol{nh}: list {h}op{nh}: post   {h}oi{nh}: info {h}ov{nh}: load+verify {h}or{nh}: revoke
Contracts  {s}cu: unseal{ns}{h}{nh}          {h}ct{nh}: talk {h}cn{nh}: negotiate
General    {h} h{nh}: help {h} u{nh}: update {h} q{nh}: quit {h} d{nh}: donate
Keys       {h}kl{nh}: list {h}ke{nh}: export {h}kn{nh}: new  {h}ki{nh}: import
{b}{"="*80}{ns}
'''

PROMPT = f'{b}ratelance> {nb}'

ABOUT = f'''
Repository: {h}https://github.com/ProgramCrafter/ratelance/{nh}
TG channel: {h}https://t.me/ratelance{nh}
'''.strip()
