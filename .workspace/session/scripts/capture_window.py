import Quartz, sys
title_substr = sys.argv[1]
out = sys.argv[2]
windows = Quartz.CGWindowListCopyWindowInfo(Quartz.kCGWindowListOptionOnScreenOnly, Quartz.kCGNullWindowID)
best = None
for w in windows:
    name = w.get('kCGWindowName','') or ''
    if title_substr.lower() in name.lower():
        best = w
        break
if not best:
    print("not found. all windows:")
    for w in windows:
        print(' -', w.get('kCGWindowOwnerName',''), '|', w.get('kCGWindowName',''))
    sys.exit(1)
wid = best['kCGWindowNumber']
image = Quartz.CGWindowListCreateImage(Quartz.CGRectNull, Quartz.kCGWindowListOptionIncludingWindow, wid, Quartz.kCGWindowImageBoundsIgnoreFraming)
dest = Quartz.CGImageDestinationCreateWithURL(Quartz.NSURL.fileURLWithPath_(out), "public.png", 1, None)
Quartz.CGImageDestinationAddImage(dest, image, None)
Quartz.CGImageDestinationFinalize(dest)
print("saved", out)
