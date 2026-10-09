import Quartz, sys
owner_substr = sys.argv[1]
out = sys.argv[2]
windows = Quartz.CGWindowListCopyWindowInfo(Quartz.kCGWindowListOptionOnScreenOnly, Quartz.kCGNullWindowID)
candidates = [w for w in windows if owner_substr.lower() in (w.get('kCGWindowOwnerName','') or '').lower()]
if not candidates:
    print("not found")
    sys.exit(1)
# pick the largest window (main game window, not a small panel)
best = max(candidates, key=lambda w: w['kCGWindowBounds']['Width'] * w['kCGWindowBounds']['Height'])
wid = best['kCGWindowNumber']
image = Quartz.CGWindowListCreateImage(Quartz.CGRectNull, Quartz.kCGWindowListOptionIncludingWindow, wid, Quartz.kCGWindowImageBoundsIgnoreFraming)
if image is None:
    print("capture failed")
    sys.exit(1)
dest = Quartz.CGImageDestinationCreateWithURL(Quartz.NSURL.fileURLWithPath_(out), "public.png", 1, None)
Quartz.CGImageDestinationAddImage(dest, image, None)
Quartz.CGImageDestinationFinalize(dest)
print("saved", out, "bounds", best['kCGWindowBounds'])
