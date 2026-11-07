# -*- coding: utf-8 -*-
'''Update the md5 anchor (rule 23) after the last in-line edit: da59acdd -> f40c8f39.'''
import io

OLD, NEW = 'da59acddc243222cf5e982e7489cadf6', 'f40c8f390085e2c64cdb0865233f8e6b'
for p in ['D:/workbuddy_space/strata_ws/deploy/AUDIT24_W900_W951.md',
          'D:/workbuddy_space/strata_ws/albus/w952/reply.md']:
    s = io.open(p, encoding='utf-8').read()
    n = s.count(OLD) + s.count('da59acdd')
    s = s.replace(OLD, NEW).replace('`da59acdd`', '`f40c8f39`')
    io.open(p, 'w', encoding='utf-8', newline='').write(s)
    print(p.split('/')[-1], 'replaced', n)
