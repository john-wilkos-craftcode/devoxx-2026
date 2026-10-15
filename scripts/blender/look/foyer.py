"""Upstairs furnishings; all placements fail closed against corridor clearances."""


def build(g):
    B, M, FH = g['B'], g['M'], g['FH']
    pi = 3.141592653589793
    corridor = g['corridor']
    blocks, social = [], []
    g['foyer_blocks'], g['foyer_social'] = blocks, social
    counts = {}
    for key, color, emission, strength, metal in (
        ('cloth', 0x142449, None, 0, 0), ('skirt', 0x101B35, None, 0, 0),
        ('black', 0x101216, None, 0, 0), ('red', 0xC91524, None, 0, 0),
        ('glass', 0xDAE6E8, 0xDAE6E8, 1.5, 0),
        ('white', 0xFAFAFF, 0xFAFAFF, 2, 0), ('quote', 0xA4ACB9, None, 0, 0),
        ('blue', 0x183F91, None, 0, 0), ('steel', 0x9DA6AC, None, 0, .85),
        ('teal', 0x13798E, 0x13798E, 1.2, 0)):
        M['foyer_'+key] = g['material']('foyer_'+key, color, rough=.38 if metal else .8,
                                        metal=metal, emission=emission, strength=strength)

    def box(key, x, y, w, h, z, height):
        B.box('foyer_'+key, dict(x=x, y=y, w=w, h=h), FH+z, FH+z+height)

    def overlaps(a, b):
        return (a['x'] < b['x']+b['w'] and a['x']+a['w'] > b['x']
                and a['y'] < b['y']+b['h'] and a['y']+a['h'] > b['y'])

    def label(body, loc, rot, width, height, key='quote'):
        # Measure in the FONT's local XY plane BEFORE rotating it upright.
        ob = g['text_object'](body, 1, loc, (0, 0, 0), M['foyer_'+key], .001, 0)
        g['bpy'].context.view_layer.update()
        scale = min(width/max(ob.dimensions.x, .001), height/max(ob.dimensions.y, .001))
        ob.scale = (scale, scale, scale)
        ob.rotation_euler = rot

    for wall, face in ((corridor['x'], 1), (corridor['x']+corridor['w'], -1)):
        doors = [d for d in g['doors'].values() if abs(d['wall_x']-wall) < 1]
        forbidden = [(-8, 16)]
        forbidden += [(d['yc']-4, d['yc']+4) for d in doors]
        forbidden += [(d['totem']['y']-.9, d['totem']['y']+.9) for d in doors]
        used = []

        def footprint(y, length, depth, inset=.15):
            a, b = sorted((wall+face*inset, wall+face*(inset+depth)))
            return dict(x=a, y=y-length/2, w=b-a, h=length)

        def clear(b):
            if b['x'] < 9 and b['x']+b['w'] > -4:
                return False
            lo, hi = b['y'], b['y']+b['h']
            return (lo >= corridor['y']+.15 and hi <= corridor['y']+corridor['h']-.15
                    and not any(lo < end+.04 and hi > start-.04 for start, end in forbidden)
                    and not any(overlaps(b, other) for other in used))

        def reserve(kind, wanted, length, depth, inset=.15):
            # Prefer the requested position, then the nearest legal span.
            candidates = sorted((corridor['y']+.25*k for k in range(1, int(corridor['h']*4))),
                                key=lambda y: abs(y-wanted))
            for y in candidates:
                b = footprint(y, length, depth, inset)
                if clear(b):
                    used.append(b)
                    blocks.append(b)
                    counts[kind] = counts.get(kind, 0)+1
                    return y, b
            return None

        rot = (pi/2, 0, face*pi/2)
        quotes = ('MAY THE FORCE BE WITH YOU', 'GO AHEAD, MAKE MY DAY') if face == 1 else ("I'LL BE BACK", 'HOUSTON, WE HAVE A PROBLEM')
        for wanted, quote in zip((-35, 40), quotes):
            place = reserve('quote', wanted, 6.2, .16, .155)
            if place:
                y, b = place
                box('blue', b['x'], b['y'], b['w'], b['h'], .9, 1.8)
                xf = wall+face*.325
                box('white', min(xf, xf+face*.015), y-3, .015, 6, 1, 1.6)
                label(quote, (wall+face*.35, y, FH+1.8), rot, 5.6, .9)
        for wanted in (-48, -24, 30, 55):
            place = reserve('fridge', wanted, .7, .7)
            if place:
                y, b = place
                box('red', b['x'], b['y'], .7, .7, 0, 1.9)
                xf = wall+face*.86
                box('glass', min(xf, xf+face*.02), y-.29, .02, .58, .18, 1.38)
                box('white', min(xf, xf+face*.02), y-.29, .02, .58, 1.65, .17)
                label('Coca-Cola', (wall+face*.89, y, FH+1.735), rot, .53, .12, 'red')
                social.append((wall+face*1.65, y))
        for wanted in (-37, 23, 49):
            place = reserve('bin_pair', wanted, .94, .44)
            if place:
                y, b = place
                for dy in (-.25, .25):
                    g['cylinder']('foyer_steel', wall+face*.37, y+dy, FH, FH+.75, .2, segs=12)
        # Stair-top signs stay beyond the entire landing exclusion.
        for wanted in ((-9, 17) if face == 1 else (17,)):
            place = reserve('totem', wanted, .6, .1)
            if place:
                y, b = place
                box('black', b['x'], b['y'], b['w'], .6, 0, 1.9)
                xf = wall+face*.26
                box('teal', min(xf, xf+face*.015), y-.25, .015, .5, .85, .9)
        # Sweep end-to-end 1.8 m table slots; move forward only when blocked.
        y = corridor['y']+1.05
        while y < corridor['y']+corridor['h']-1:
            b = footprint(y, 1.8, 1.43, .35)
            if not clear(b):
                y += .1
                continue
            used.append(b)
            blocks.append(b)
            counts['table'] = counts.get('table', 0)+1
            tx = min(wall+face*.35, wall+face*1.1)
            box('skirt', tx, y-.9, .75, 1.8, .3, .43)
            box('cloth', tx-.01, y-.9, .77, 1.8, .73, .02)
            for dy in (-.6, 0, .6):
                cx, cy = wall+face*1.5, y+dy
                box('black', cx-.22, cy-.22, .44, .44, .42, .03)
                bx = wall+face*1.73
                box('black', bx-.025, cy-.22, .05, .44, .72, .18)
                for dy_back in (-.19, .19):
                    box('black', bx-.012, cy+dy_back-.012, .024, .024, .45, .45)
                for dx in (-.17, .17):
                    box('black', cx+dx-.015, cy-.17, .03, .34, 0, .42)
            social.append((wall+face*2.5, y))
            y += 1.8

    # The projection screen hangs in front of the middle funnel over the grand stair, above head height.
    for key, color in (('screenM', 0xC2187A), ('screenV', 0x6A2BC9), ('screenB', 0x1F4FE0)):
        M['foyer_'+key] = g['material']('foyer_'+key, color, emission=color, strength=1.5)
    grand = next(l for l in g['venue']['links'] if l['id'] == 'grand-stair')['bounds']
    sx, y0 = grand['x']+grand['w']/2, grand['y']+grand['h']+1.8+3.1
    box('black', sx-2.5, y0, 5.0, .08, 2.6, 2.9)
    for i, key in enumerate(('screenM', 'screenV', 'screenB')):
        box(key, sx-2.4+i*1.6, y0+.08, 1.6, .02, 2.7, 2.7)
    label('BUILD AGENTS + DEBUG', (sx, y0+.12, FH+4.55), (pi/2, 0, pi), 4.2, .5, 'white')
    label('DEVOXX', (sx, y0+.12, FH+3.3), (pi/2, 0, pi), 2.2, .38, 'white')
    counts['screen'] = 1
    print('CHECK foyer:', counts)
