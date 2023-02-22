from colors import nh, h, nb, b, ns, s

PROMPT_SINGLE = f'''{b}{"="*80}{ns}
Offers     {h}ol{nh}: list {h}op{nh}: post   {h}oi{nh}: info {h}oa{nh}: advanced {h}or{nh}: revoke
Jobs       {h}jl{nh}: list {h}jp{nh}: post   {h}ji{nh}: info {h}ja{nh}: advanced {h}jr{nh}: revoke {h}jd{nh}: delegate
Contracts  {h}cl{nh}: list {s}cu: unseal{ns} {h}ci{nh}: info {h}ca{nh}: advanced {h}ct{nh}: talk   {h}cn{nh}: negotiate
General    {h} h{nh}: help {h} u{nh}: update {h} q{nh}: quit
Keys       {h}kl{nh}: list {h}ke{nh}: export {h}kn{nh}: new  {h}ki{nh}: import
{b}{"="*80}{ns}
'''

PROMPT = f'{b}ratelance> {nb}'

ABOUT = f'''
Repository: {h}https://github.com/ProgramCrafter/ratelance/{nh}
TG channel: {h}https://t.me/ratelance{nh}
'''.strip()
