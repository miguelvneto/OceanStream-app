"""Native safe-area inspection. No session, network or app-exit operations."""
import math


def remaining_insets(top, bottom, reserved_top, reserved_bottom, native_height, kivy_height):
    """Convert only overlap with the render surface, avoiding double padding."""
    values = (top, bottom, reserved_top, reserved_bottom, native_height, kivy_height)
    if not all(math.isfinite(v) and v >= 0 for v in values) or native_height == 0:
        raise ValueError('Invalid native geometry')
    scale = kivy_height / native_height
    return (max(0, top-reserved_top)*scale, max(0, bottom-reserved_bottom)*scale)


def android_insets(activity, autoclass, kivy_height):
    """Called on the Android UI thread; all native dimensions are pixels."""
    version = autoclass('android.os.Build$VERSION').SDK_INT
    if version < 23:
        return (0, 0)  # Non-fullscreen window uses the system's fitted content.
    decor = activity.getWindow().getDecorView()
    surface = activity.getSurface()
    insets = decor.getRootWindowInsets()
    if insets is None or surface.getHeight() <= 0:
        raise ValueError('Insets not available before window layout')
    if version >= 30:
        types = autoclass('android.view.WindowInsets$Type')
        areas = insets.getInsets(types.systemBars() | types.displayCutout()
                                 | types.mandatorySystemGestures())
        top, bottom = areas.top, areas.bottom
    else:
        top, bottom = insets.getStableInsetTop(), insets.getStableInsetBottom()
        if version >= 28:
            cutout = insets.getDisplayCutout()
            if cutout:
                top, bottom = max(top, cutout.getSafeInsetTop()), max(bottom, cutout.getSafeInsetBottom())
        if version >= 29:
            bottom = max(bottom, insets.getMandatorySystemGestureInsets().bottom)
    # Pyjnius copies Java array output into the supplied Python lists.
    surface_pos, decor_pos = [0, 0], [0, 0]
    surface.getLocationOnScreen(surface_pos)
    decor.getLocationOnScreen(decor_pos)
    reserved_top = max(0, surface_pos[1]-decor_pos[1])
    reserved_bottom = max(0, decor_pos[1]+decor.getHeight()-surface_pos[1]-surface.getHeight())
    return remaining_insets(top, bottom, reserved_top, reserved_bottom,
                            surface.getHeight(), kivy_height)


def ios_insets(autoclass, kivy_height):
    """Use the active SDL controller view's safe layout in UIKit points."""
    app = autoclass('UIApplication').sharedApplication()
    windows = app.windows()
    window = None
    for index in range(windows.count()):
        candidate = windows.objectAtIndex_(index)
        if candidate.isKeyWindow():
            window = candidate
            break
    if window is None:
        raise ValueError('No active iOS window')
    view = window.rootViewController().view()
    bounds = view.bounds()
    safe = view.safeAreaLayoutGuide().layoutFrame()
    top = max(0, safe.origin.y-bounds.origin.y)
    bottom = max(0, bounds.origin.y+bounds.size.height-safe.origin.y-safe.size.height)
    # safeAreaLayoutGuide is already relative to this view, so no second inset.
    return remaining_insets(top, bottom, 0, 0, bounds.size.height, kivy_height)


def request_safe_area(platform, kivy_height, callback):
    """Deliver (top, bottom), or None if native inspection is unavailable.

    Android is queried on its UI thread; the caller marshals results to Kivy.
    iOS SDL runs the Kivy event loop on the UIKit main thread. If a different
    bootstrap does not, keep the fallback rather than access UIKit off-thread.
    """
    if platform == 'android':
        try:
            from android import mActivity
            from android.runnable import run_on_ui_thread
            from jnius import autoclass

            @run_on_ui_thread
            def query():
                try:
                    result = android_insets(mActivity, autoclass, kivy_height)
                except Exception:
                    result = None
                callback(result)
            query()
        except Exception:
            callback(None)
    elif platform == 'ios':
        try:
            from pyobjus import autoclass
            if not autoclass('NSThread').isMainThread():
                raise RuntimeError('UIKit requires its main thread')
            result = ios_insets(autoclass, kivy_height)
        except Exception:
            result = None
        callback(result)
    else:
        callback((0, 0))


def back_action(platform, key, screen, blocked=False, drawer_open=False):
    """Overview always delegates to Kivy's native Android background behavior."""
    if platform != 'android' or key != 27 or blocked:
        return None
    if screen == 'equipamento' and drawer_open:
        return 'close_drawer'
    if screen in ('configuracao', 'equipamento'):
        return 'overview'
    return None
