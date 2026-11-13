use super::*;
use std::{
    ptr::{null, null_mut},
    sync::mpsc,
    thread::{self, JoinHandle},
};
use windows_sys::Win32::{
    Foundation::*,
    Graphics::Gdi::*,
    System::LibraryLoader::GetModuleHandleW,
    UI::{HiDpi::*, WindowsAndMessaging::*},
};

const UPDATE: u32 = WM_APP + 71;
const CLOSE: u32 = WM_APP + 72;
const CLASS: &str = "DragonLab.Native.PassiveOverlay.0200";

pub(super) struct Runtime {
    hwnd: usize,
    shared: Arc<Shared>,
    thread: Option<JoinHandle<()>>,
    last: Option<Scene>,
}
impl Runtime {
    pub fn start() -> Result<Self, String> {
        let shared = Arc::new(Shared::default());
        let worker_shared = Arc::clone(&shared);
        let (ready, rx) = mpsc::sync_channel(1);
        let handle = thread::Builder::new()
            .name("DragonLab-Native-Overlay".into())
            .spawn(move || unsafe { run(worker_shared, ready) })
            .map_err(|e| e.to_string())?;
        let hwnd = rx
            .recv_timeout(std::time::Duration::from_secs(5))
            .map_err(|e| e.to_string())??;
        Ok(Self {
            hwnd,
            shared,
            thread: Some(handle),
            last: None,
        })
    }
    pub fn submit(&mut self, scene: Scene) -> i32 {
        if self.thread.as_ref().is_none_or(|h| h.is_finished())
            || self.shared.presentation_errors.load(Ordering::Acquire) != 0
        {
            return -7;
        }
        if self.last.as_ref() == Some(&scene) {
            return 1;
        }
        self.last = Some(scene.clone());
        let seq = self.shared.submitted.fetch_add(1, Ordering::Relaxed) + 1;
        let Ok(mut pending) = self.shared.pending.lock() else {
            return -4;
        };
        let wake = pending.is_none();
        if !wake {
            self.shared.coalesced.fetch_add(1, Ordering::Relaxed);
        }
        *pending = Some((seq, scene));
        drop(pending);
        if wake && unsafe { PostMessageW(self.hwnd as HWND, UPDATE, 0, 0) } == 0 {
            return -8;
        }
        0
    }
    pub fn close(&mut self) {
        if self.thread.is_none() {
            return;
        }
        unsafe {
            PostMessageW(self.hwnd as HWND, CLOSE, 0, 0);
        }
        if let Some(handle) = self.thread.take() {
            let _ = handle.join();
        }
    }
    pub fn status(&self) -> serde_json::Value {
        let h = self.hwnd as HWND;
        unsafe {
            let style = GetWindowLongPtrW(h, GWL_EXSTYLE) as u32;
            let mut rectangle = std::mem::zeroed::<RECT>();
            GetWindowRect(h, &mut rectangle);
            serde_json::json!({"running":self.thread.as_ref().is_some_and(|t|!t.is_finished()),"visible":IsWindowVisible(h)!=0,
                "submitted":self.shared.submitted.load(Ordering::Relaxed),"painted":self.shared.painted.load(Ordering::Acquire),"coalesced":self.shared.coalesced.load(Ordering::Relaxed),
                "presentations":self.shared.presentations.load(Ordering::Relaxed),"geometry_updates":self.shared.geometry_updates.load(Ordering::Relaxed),
                "shows":self.shared.shows.load(Ordering::Relaxed),"hides":self.shared.hides.load(Ordering::Relaxed),"presentation_errors":self.shared.presentation_errors.load(Ordering::Acquire),
                "presentation":"atomic-layered",
                "transparent":style&WS_EX_TRANSPARENT!=0,"no_activate":style&WS_EX_NOACTIVATE!=0,"layered":style&WS_EX_LAYERED!=0,
                "box":[rectangle.left,rectangle.top,rectangle.right,rectangle.bottom]})
        }
    }
    pub fn flags(&self) -> u32 {
        u32::from(
            self.thread.as_ref().is_some_and(|t| !t.is_finished())
                && self.shared.presentation_errors.load(Ordering::Acquire) == 0,
        ) | (u32::from(unsafe { IsWindowVisible(self.hwnd as HWND) } != 0) << 1)
    }
}
impl Drop for Runtime {
    fn drop(&mut self) {
        self.close();
    }
}

fn wide(s: &str) -> Vec<u16> {
    s.encode_utf16().chain(Some(0)).collect()
}
unsafe fn run(shared: Arc<Shared>, ready: mpsc::SyncSender<Result<usize, String>>) {
    let old_dpi = SetThreadDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2);
    let instance = GetModuleHandleW(null());
    let name = wide(CLASS);
    let class = WNDCLASSW {
        lpfnWndProc: Some(wndproc),
        hInstance: instance,
        lpszClassName: name.as_ptr(),
        ..std::mem::zeroed()
    };
    if RegisterClassW(&class) == 0 {
        let _ = ready.send(Err(format!("RegisterClassW: {}", GetLastError())));
        return;
    }
    let mut state = Box::new(WindowState::new(shared));
    let pointer = &mut *state as *mut WindowState;
    let hwnd = CreateWindowExW(
        WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW | WS_EX_TOPMOST,
        name.as_ptr(),
        wide("DragonLab · Guía nativa").as_ptr(),
        WS_POPUP | WS_DISABLED,
        0,
        0,
        1,
        1,
        null_mut(),
        null_mut(),
        instance,
        pointer.cast(),
    );
    if hwnd.is_null() {
        let _ = ready.send(Err(format!("CreateWindowExW: {}", GetLastError())));
        UnregisterClassW(name.as_ptr(), instance);
        return;
    }
    // Do not call SetLayeredWindowAttributes: it switches layered windows to
    // redirected WM_PAINT mode and prevents UpdateLayeredWindow until reset.
    if ready.send(Ok(hwnd as usize)).is_err() {
        DestroyWindow(hwnd);
        UnregisterClassW(name.as_ptr(), instance);
        return;
    }
    let mut message = std::mem::zeroed::<MSG>();
    while GetMessageW(&mut message, null_mut(), 0, 0) > 0 {
        TranslateMessage(&message);
        DispatchMessageW(&message);
    }
    if IsWindow(hwnd) != 0 {
        DestroyWindow(hwnd);
    }
    drop(state);
    UnregisterClassW(name.as_ptr(), instance);
    if !old_dpi.is_null() {
        SetThreadDpiAwarenessContext(old_dpi);
    }
}

unsafe extern "system" fn wndproc(hwnd: HWND, msg: u32, w: WPARAM, l: LPARAM) -> LRESULT {
    if msg == WM_NCCREATE {
        let create = &*(l as *const CREATESTRUCTW);
        SetWindowLongPtrW(hwnd, GWLP_USERDATA, create.lpCreateParams as isize);
        return 1;
    }
    if msg == WM_NCHITTEST {
        return HTTRANSPARENT as LRESULT;
    }
    if msg == WM_MOUSEACTIVATE {
        return MA_NOACTIVATE as LRESULT;
    }
    if msg == WM_ERASEBKGND {
        return 1;
    }
    if msg == CLOSE {
        DestroyWindow(hwnd);
        return 0;
    }
    if msg == WM_DESTROY {
        PostQuitMessage(0);
        return 0;
    }
    let pointer = GetWindowLongPtrW(hwnd, GWLP_USERDATA) as *mut WindowState;
    if !pointer.is_null() {
        let state = &mut *pointer;
        if msg == UPDATE {
            // Taking the slot under one mutex means rapid producers replace a
            // scene rather than building a backlog of paint work.
            let next = state.shared.pending.lock().ok().and_then(|mut p| p.take());
            if let Some((seq, scene)) = next {
                let bounds = scene.bounds();
                state.scene = Some(scene);
                state.sequence = seq;
                if let Some(bounds) = bounds {
                    // Position, size and the completed bitmap are committed
                    // together, so a resize cannot expose an empty frame.
                    if !state.present(hwnd, bounds) {
                        state
                            .shared
                            .presentation_errors
                            .fetch_add(1, Ordering::Release);
                    }
                } else {
                    if state.shown {
                        ShowWindow(hwnd, SW_HIDE);
                        state.shown = false;
                        state.shared.hides.fetch_add(1, Ordering::Relaxed);
                    }
                    state.shared.painted.store(seq, Ordering::Release);
                }
            }
            return 0;
        }
        if msg == WM_PAINT {
            // Pixels are owned by the compositor after UpdateLayeredWindow.
            // Validate exposure messages without erasing or repainting them.
            ValidateRect(hwnd, null());
            return 0;
        }
    }
    DefWindowProcW(hwnd, msg, w, l)
}

struct Buffer {
    dc: HDC,
    bitmap: HBITMAP,
    old: HGDIOBJ,
    w: i32,
    h: i32,
}
impl Buffer {
    unsafe fn new(source: HDC, w: i32, h: i32) -> Option<Self> {
        let dc = CreateCompatibleDC(source);
        if dc.is_null() {
            return None;
        }
        let bitmap = CreateCompatibleBitmap(source, w, h);
        if bitmap.is_null() {
            DeleteDC(dc);
            return None;
        }
        let old = SelectObject(dc, bitmap);
        Some(Self {
            dc,
            bitmap,
            old,
            w,
            h,
        })
    }
}
impl Drop for Buffer {
    fn drop(&mut self) {
        unsafe {
            SelectObject(self.dc, self.old);
            DeleteObject(self.bitmap);
            DeleteDC(self.dc);
        }
    }
}
struct WindowState {
    shared: Arc<Shared>,
    scene: Option<Scene>,
    sequence: u64,
    bounds: Option<Bounds>,
    buffer: Option<Buffer>,
    font: HFONT,
    font_size: i32,
    guide_font: HFONT,
    guide_font_size: i32,
    shown: bool,
}
impl WindowState {
    unsafe fn new(shared: Arc<Shared>) -> Self {
        Self {
            shared,
            scene: None,
            sequence: 0,
            bounds: None,
            buffer: None,
            font: make_font(12),
            font_size: 12,
            guide_font: make_font(12),
            guide_font_size: 12,
            shown: false,
        }
    }
    unsafe fn present(&mut self, hwnd: HWND, bounds: Bounds) -> bool {
        let target = GetDC(null_mut());
        if target.is_null() {
            return false;
        }
        let mut presented = false;
        if let Some(scene) = self.scene.as_ref() {
            if self
                .buffer
                .as_ref()
                .is_none_or(|b| b.w != bounds.w || b.h != bounds.h)
            {
                self.buffer = Buffer::new(target, bounds.w, bounds.h);
            }
            let font_size = actor_font_pixels(scene);
            if font_size != self.font_size {
                DeleteObject(self.font);
                self.font = make_font(font_size);
                self.font_size = font_size;
            }
            let guide_size = guide_font_pixels(&scene.guide);
            if guide_size != self.guide_font_size {
                DeleteObject(self.guide_font);
                self.guide_font = make_font(guide_size);
                self.guide_font_size = guide_size;
            }
            if let Some(buffer) = &self.buffer {
                let dc = buffer.dc;
                let brush = CreateSolidBrush(COLOR_KEY);
                FillRect(
                    dc,
                    &RECT {
                        left: 0,
                        top: 0,
                        right: bounds.w,
                        bottom: bounds.h,
                    },
                    brush,
                );
                DeleteObject(brush);
                if scene.visible {
                    draw_field(dc, scene, bounds, self.font);
                }
                if scene.guide.visible {
                    draw_guide(dc, &scene.guide, bounds, self.guide_font);
                }
                let destination = POINT {
                    x: bounds.x,
                    y: bounds.y,
                };
                let size = SIZE {
                    cx: bounds.w,
                    cy: bounds.h,
                };
                let source = POINT { x: 0, y: 0 };
                if UpdateLayeredWindow(
                    hwnd,
                    target,
                    &destination,
                    &size,
                    dc,
                    &source,
                    COLOR_KEY,
                    null(),
                    ULW_COLORKEY,
                ) != 0
                {
                    if self.bounds != Some(bounds) {
                        self.shared.geometry_updates.fetch_add(1, Ordering::Relaxed);
                    }
                    self.bounds = Some(bounds);
                    if !self.shown {
                        ShowWindow(hwnd, SW_SHOWNOACTIVATE);
                        self.shown = true;
                        self.shared.shows.fetch_add(1, Ordering::Relaxed);
                    }
                    self.shared.presentations.fetch_add(1, Ordering::Relaxed);
                    self.shared.painted.store(self.sequence, Ordering::Release);
                    presented = true;
                }
            }
        }
        ReleaseDC(null_mut(), target);
        presented
    }
}

fn guide_font_pixels(guide: &Guide) -> i32 {
    let width = (guide.bar[2] - guide.bar[0]).hypot(guide.bar[3] - guide.bar[1]);
    let scale = (width / 480.).clamp(0.85, 1.1);
    let requested = if guide.font_size > 0. {
        guide.font_size
    } else {
        12.
    };
    (requested * scale).round().clamp(11., 13.) as i32
}
fn actor_font_pixels(scene: &Scene) -> i32 {
    if scene.style.font_size.is_finite() && scene.style.font_size > 0. {
        let scale = ((scene.area[2] - scene.area[0]) / scene.viewport[0]).clamp(0.75, 1.25);
        (scene.style.font_size * scale).round().clamp(10., 15.) as i32
    } else {
        12
    }
}
impl Drop for WindowState {
    fn drop(&mut self) {
        self.buffer.take();
        unsafe {
            DeleteObject(self.font);
            DeleteObject(self.guide_font);
        }
    }
}
unsafe fn make_font(size: i32) -> HFONT {
    CreateFontW(
        -size,
        0,
        0,
        0,
        600,
        0,
        0,
        0,
        DEFAULT_CHARSET as u32,
        OUT_DEFAULT_PRECIS as u32,
        CLIP_DEFAULT_PRECIS as u32,
        ANTIALIASED_QUALITY as u32,
        DEFAULT_PITCH as u32,
        wide("Bahnschrift").as_ptr(),
    )
}
fn point(x: f64, y: f64) -> POINT {
    POINT {
        x: x.round_ties_even().clamp(-2_000_000., 2_000_000.) as i32,
        y: y.round_ties_even().clamp(-2_000_000., 2_000_000.) as i32,
    }
}
unsafe fn line(dc: HDC, points: &[POINT], colour: u32, width: i32) {
    if points.len() < 2 {
        return;
    }
    let brush = LOGBRUSH {
        lbStyle: BS_SOLID,
        lbColor: colour,
        lbHatch: 0,
    };
    let pen = ExtCreatePen(
        (PS_GEOMETRIC | PS_SOLID | PS_ENDCAP_ROUND | PS_JOIN_ROUND) as u32,
        width as u32,
        &brush,
        0,
        null(),
    );
    if pen.is_null() {
        return;
    }
    let old = SelectObject(dc, pen);
    Polyline(dc, points.as_ptr(), points.len() as i32);
    SelectObject(dc, old);
    DeleteObject(pen);
}
unsafe fn paths<F: Fn(f64, f64) -> POINT>(
    dc: HDC,
    path: &[Option<[f64; 2]>],
    project: F,
    colour: u32,
    width: i32,
) {
    let mut run = Vec::with_capacity(path.len());
    for item in path {
        match item {
            Some([x, y]) => run.push(project(*x, *y)),
            None => {
                line(dc, &run, colour, width);
                run.clear();
            }
        }
    }
    line(dc, &run, colour, width);
}
unsafe fn text(dc: HDC, x: f64, y: f64, value: &str, colour: u32, font: HFONT, width: i32) {
    text_bounded(dc, x, y, value, colour, font, 0, width);
}
#[allow(clippy::too_many_arguments)]
unsafe fn text_bounded(
    dc: HDC,
    x: f64,
    y: f64,
    value: &str,
    colour: u32,
    font: HFONT,
    region_left: i32,
    region_right: i32,
) {
    if value.is_empty() {
        return;
    }
    let width = (region_right - region_left).max(24);
    let value = wide(value);
    let old_font = SelectObject(dc, font);
    SetBkMode(dc, TRANSPARENT as i32);
    SetTextColor(dc, colour);
    let mut measured = RECT {
        left: 0,
        top: 0,
        right: width,
        bottom: 0,
    };
    DrawTextW(
        dc,
        value.as_ptr(),
        (value.len() - 1) as i32,
        &mut measured,
        DT_CALCRECT | DT_SINGLELINE | DT_NOPREFIX,
    );
    let text_height = (measured.bottom - measured.top).max(1);
    let actual = (measured.right - measured.left + 2).min((width - 12).max(1));
    let left = (x.round() as i32 - actual / 2).clamp(
        region_left + 4,
        (region_right - actual - 8).max(region_left + 4),
    );
    let top = y.round() as i32 - text_height / 2;
    let brush = CreateSolidBrush(BG);
    let old_brush = SelectObject(dc, brush);
    let old_pen = SelectObject(dc, GetStockObject(NULL_PEN));
    RoundRect(
        dc,
        left - 4,
        top - 2,
        left + actual + 4,
        top + text_height + 2,
        8,
        8,
    );
    SelectObject(dc, old_pen);
    SelectObject(dc, old_brush);
    DeleteObject(brush);
    let mut rectangle = RECT {
        left,
        top,
        right: left + actual,
        bottom: top + text_height,
    };
    DrawTextW(
        dc,
        value.as_ptr(),
        (value.len() - 1) as i32,
        &mut rectangle,
        DT_LEFT | DT_SINGLELINE | DT_NOPREFIX | DT_END_ELLIPSIS,
    );
    SelectObject(dc, old_font);
}
unsafe fn draw_field(dc: HDC, scene: &Scene, b: Bounds, font: HFONT) {
    let clip = SaveDC(dc);
    let ox = scene.area[0] - b.x as f64;
    let oy = scene.area[1] - b.y as f64;
    let w = scene.area[2] - scene.area[0];
    let h = scene.area[3] - scene.area[1];
    let field_h = scene.field_height();
    IntersectClipRect(
        dc,
        ox.floor() as i32,
        oy.floor() as i32,
        (ox + w).ceil() as i32,
        (oy + field_h).ceil() as i32,
    );
    let project = |x: f64, y: f64| {
        point(
            ox + x * w / scene.viewport[0],
            oy + y * h / scene.viewport[1],
        )
    };
    for path in &scene.planned {
        paths(
            dc,
            path,
            project,
            color(&scene.style.color, GREEN),
            stroke(scene.style.width, 3),
        );
    }
    for path in scene.observed.values() {
        paths(
            dc,
            path,
            project,
            color(&scene.style.observed_color, OBSERVED),
            stroke(scene.style.width * 0.7, 2),
        );
    }
    for item in &scene.annotations {
        paths(
            dc,
            &item.points,
            project,
            color(&item.color, OBSERVED),
            stroke(item.width, 2),
        );
        if !item.label.is_empty() {
            let p = project(item.x, item.y);
            text(
                dc,
                p.x as f64,
                p.y as f64,
                &item.label,
                color(&item.color, TEXT),
                font,
                b.w,
            );
        }
    }
    for player in &scene.players {
        if player.dead {
            continue;
        }
        let raw = project(player.x, player.y);
        let colour = player.colour();
        let (min_x, max_x, min_y, max_y) = (
            ox + 20.,
            (ox + w - 20.).max(ox + 20.),
            oy + 35.,
            (oy + field_h - 25.).max(oy + 35.),
        );
        let x = (raw.x as f64).clamp(min_x, max_x);
        let y = (raw.y as f64).clamp(min_y, max_y);
        let outside = x != raw.x as f64 || y != raw.y as f64;
        if outside {
            let angle = (raw.y as f64 - y).atan2(raw.x as f64 - x);
            let (dx, dy) = (angle.cos(), angle.sin());
            line(
                dc,
                &[
                    point(x - 10. * dx, y - 10. * dy),
                    point(x, y),
                    point(x - 7. * dx - 4. * dy, y - 7. * dy + 4. * dx),
                ],
                colour,
                3,
            );
            line(
                dc,
                &[
                    point(x, y),
                    point(x - 7. * dx + 4. * dy, y - 7. * dy - 4. * dx),
                ],
                colour,
                3,
            );
        } else {
            line(dc, &[point(x - 8., y), point(x + 8., y)], colour, 3);
            line(dc, &[point(x, y), point(x, y - 12.)], colour, 3);
        }
    }
    let labels = actor_labels(scene, w, field_h, actor_font_pixels(scene));
    // Leaders explain a displaced label while keeping the actual actor marker.
    for label in &labels {
        for index in &label.members {
            let player = &scene.players[*index];
            let raw = project(player.x, player.y);
            let x = (raw.x as f64).clamp(ox + 20., (ox + w - 20.).max(ox + 20.));
            let y = (raw.y as f64).clamp(oy + 35., (oy + field_h - 25.).max(oy + 35.));
            let center = [ox + label.x + label.width / 2., oy + label.y];
            if (center[0] - x).hypot(center[1] - y) > 35. {
                line(
                    dc,
                    &[point(x, y), point(center[0], center[1])],
                    player.colour(),
                    1,
                );
            }
        }
    }
    for label in labels {
        text_bounded(
            dc,
            ox + label.x + label.width / 2.,
            oy + label.y,
            &label.value,
            label.colour,
            font,
            (ox + label.x).ceil() as i32,
            (ox + label.x + label.width).floor() as i32,
        );
    }
    RestoreDC(dc, clip);
}
unsafe fn draw_guide(dc: HDC, guide: &Guide, b: Bounds, font: HFONT) {
    let [x1, y1, x2, y2] = guide.bar;
    let ox = b.x as f64;
    let oy = b.y as f64;
    let colour = if guide.updating {
        MUTED
    } else if guide.measured && !guide.blocked {
        GREEN
    } else {
        ORANGE
    };
    let mut label = guide.label.clone();
    if let Some(power) = guide.power.filter(|p| *p > 0. && *p <= guide.max_power) {
        let fraction = (power / guide.max_power).clamp(0., 1.);
        let x = x1 + (x2 - x1) * fraction - ox;
        let y = y1 + (y2 - y1) * fraction - oy;
        line(
            dc,
            &[point(x1 - ox, y1 - oy), point(x2 - ox, y2 - oy)],
            GREEN,
            1,
        );
        line(dc, &[point(x, y - 14.), point(x, y + 6.)], colour, 2);
        line(
            dc,
            &[
                point(x - 4., y - 17.),
                point(x, y - 12.),
                point(x + 4., y - 17.),
                point(x - 4., y - 17.),
            ],
            colour,
            2,
        );
        if label.is_empty() {
            label = if guide.blocked {
                format!("Bloqueado · {power:.0}")
            } else {
                format!("{power:.0} · {:.0}%", fraction * 100.)
            };
        }
    } else if label.is_empty() {
        label = if guide.updating {
            "Calculando…"
        } else {
            "Sin guía"
        }
        .into();
    }
    let center = (x1 + x2) / 2. - ox;
    let caption_width = ((x2 - x1).abs() * 0.7).clamp(80., 220.) as i32;
    text_bounded(
        dc,
        center,
        y1.min(y2) - 26. - oy,
        &label,
        if guide.power.is_some() { colour } else { MUTED },
        font,
        (center - caption_width as f64 / 2.).floor() as i32,
        (center + caption_width as f64 / 2.).ceil() as i32,
    );
}

#[cfg(test)]
mod tests {
    use super::*;
    // These checks inspect process-global Win32/GDI state and must serialize.
    static UI_TEST_LOCK: Mutex<()> = Mutex::new(());
    #[test]
    fn latest_scene_is_painted_without_focus_or_input() {
        let _guard = UI_TEST_LOCK.lock().unwrap();
        let before = unsafe { GetForegroundWindow() };
        let gdi_before = unsafe {
            windows_sys::Win32::System::Threading::GetGuiResources(
                windows_sys::Win32::System::Threading::GetCurrentProcess(),
                0,
            )
        };
        let mut runtime = Runtime::start().unwrap();
        let mut scene = Scene {
            area: [-2000., -2000., -1200., -1400.],
            visible: true,
            planned: vec![vec![Some([10., 30.]), Some([500., 300.])]],
            ..Scene::default()
        };
        assert_eq!(runtime.submit(scene.clone()), 0);
        assert_eq!(runtime.submit(scene.clone()), 1);
        for i in 0..200 {
            scene.planned[0][1] = Some([500., 300. + i as f64 / 100.]);
            runtime.submit(scene.clone());
        }
        let until = std::time::Instant::now() + std::time::Duration::from_secs(2);
        loop {
            let s = runtime.status();
            if s["painted"] == s["submitted"] {
                break;
            }
            assert!(std::time::Instant::now() < until);
            thread::sleep(std::time::Duration::from_millis(5));
        }
        let status = runtime.status();
        assert_eq!(status["transparent"], true);
        assert_eq!(status["no_activate"], true);
        assert_eq!(status["layered"], true);
        assert_eq!(status["presentation"], "atomic-layered");
        assert_eq!(status["presentation_errors"], 0);
        assert_eq!(status["shows"], 1);
        assert_eq!(status["hides"], 0);
        assert_eq!(status["geometry_updates"], 1);
        let idle_presentations = status["presentations"].clone();
        thread::sleep(std::time::Duration::from_millis(25));
        assert_eq!(runtime.status()["presentations"], idle_presentations);
        assert_eq!(unsafe { GetForegroundWindow() }, before);
        runtime.close();
        let gdi_after = unsafe {
            windows_sys::Win32::System::Threading::GetGuiResources(
                windows_sys::Win32::System::Threading::GetCurrentProcess(),
                0,
            )
        };
        assert!(
            gdi_after <= gdi_before + 1,
            "GDI objects leaked: {gdi_before} -> {gdi_after}"
        );
    }

    #[test]
    fn resize_and_visibility_commit_complete_frames_without_repeated_show_calls() {
        let _guard = UI_TEST_LOCK.lock().unwrap();
        let before = unsafe { GetForegroundWindow() };
        let mut runtime = Runtime::start().unwrap();
        let mut scene = Scene {
            area: [-1900., -1800., -1100., -1200.],
            visible: true,
            planned: vec![vec![Some([20., 30.]), Some([700., 400.])]],
            ..Scene::default()
        };
        fn settle(runtime: &Runtime) {
            let until = std::time::Instant::now() + std::time::Duration::from_secs(2);
            loop {
                let status = runtime.status();
                assert_eq!(status["presentation_errors"], 0);
                if status["painted"] == status["submitted"] {
                    return;
                }
                assert!(
                    std::time::Instant::now() < until,
                    "overlay presentation stalled"
                );
                thread::sleep(std::time::Duration::from_millis(2));
            }
        }
        runtime.submit(scene.clone());
        settle(&runtime);
        for offset in 1..=12 {
            scene.area[0] = -1900. + offset as f64;
            scene.area[2] = -1100. + offset as f64 * 2.;
            runtime.submit(scene.clone());
            settle(&runtime);
            let expected = scene.bounds().unwrap();
            assert_eq!(
                runtime.status()["box"],
                serde_json::json!([
                    expected.x,
                    expected.y,
                    expected.x + expected.w,
                    expected.y + expected.h
                ])
            );
        }
        let live = runtime.status();
        assert_eq!(live["shows"], 1);
        assert_eq!(live["hides"], 0);
        scene.visible = false;
        runtime.submit(scene.clone());
        settle(&runtime);
        assert_eq!(runtime.status()["visible"], false);
        assert_eq!(runtime.status()["hides"], 1);
        scene.style.width = 4.;
        runtime.submit(scene.clone());
        settle(&runtime);
        assert_eq!(runtime.status()["hides"], 1);
        scene.visible = true;
        runtime.submit(scene);
        settle(&runtime);
        let restored = runtime.status();
        assert_eq!(restored["shows"], 2);
        assert_eq!(restored["hides"], 1);
        assert_eq!(restored["presentation_errors"], 0);
        assert_eq!(unsafe { GetForegroundWindow() }, before);
        runtime.close();
    }

    #[test]
    fn guide_typography_is_bounded_in_physical_pixels_at_different_game_scales() {
        for width in [200., 360., 480., 740., 1400.] {
            let guide = Guide {
                bar: [0., 0., width, 0.],
                ..Guide::default()
            };
            assert!((11..=13).contains(&guide_font_pixels(&guide)));
        }
        let guide = Guide {
            bar: [0., 0., 2000., 0.],
            font_size: 72.,
            ..Guide::default()
        };
        assert_eq!(guide_font_pixels(&guide), 13);
    }

    #[test]
    fn exports_only_own_offscreen_render_for_visual_qa() {
        let _guard = UI_TEST_LOCK.lock().unwrap();
        // This renders synthetic geometry into a private compatible bitmap.
        // No desktop pixels, app windows or screen captures are read.
        unsafe {
            let scene:Scene=serde_json::from_value(serde_json::json!({
                "box":[0,0,710,505],"viewport":[900,640],"visible":true,
                "style":{"color":"#BBFF00","width":3},
                "planned":[(0..=120).map(|i|{let t=i as f64/2.;Some([100.+10.*t,400.-0.25*t*(60.-t)])}).collect::<Vec<_>>()],
                "observed":{"fixture":(0..=60).map(|i|{let t=i as f64;Some([100.+10.*t,405.-0.24*t*(60.-t)])}).collect::<Vec<_>>()},
                "players":[{"x":100,"y":400,"hero":true,"role":"hero","label":"TÚ"},{"x":700,"y":400,"selected":true,"role":"enemy","label":"▶ ENEMIGO 1"},{"x":1100,"y":300,"role":"enemy","number":2,"label":"ENEMIGO 2"},{"x":400,"y":450,"role":"ally","label":"ALIADO"}],
                "annotations":[{"points":[[450,0],[450,516]],"color":"#D69CFC","width":1,"label":"Mirror","x":450,"y":43},{"points":[[650,0],[650,516]],"color":"#7BCDDB","width":1,"label":"Tornado","x":650,"y":43}],
                "guide":{"visible":true,"bar":[63,480,647,480],"power":321,"maxPower":400,"label":"321 · 80%","measured":true}
            })).unwrap();
            assert!(scene.valid());
            let bounds = scene.bounds().unwrap();
            let screen = GetDC(null_mut());
            assert!(!screen.is_null());
            let buffer = Buffer::new(screen, bounds.w, bounds.h).unwrap();
            let brush = CreateSolidBrush(COLOR_KEY);
            FillRect(
                buffer.dc,
                &RECT {
                    left: 0,
                    top: 0,
                    right: bounds.w,
                    bottom: bounds.h,
                },
                brush,
            );
            DeleteObject(brush);
            let font = make_font(12);
            let guide_font = make_font(guide_font_pixels(&scene.guide));
            draw_field(buffer.dc, &scene, bounds, font);
            draw_guide(buffer.dc, &scene.guide, bounds, guide_font);
            DeleteObject(font);
            DeleteObject(guide_font);
            let mut info = BITMAPINFO {
                bmiHeader: BITMAPINFOHEADER {
                    biSize: std::mem::size_of::<BITMAPINFOHEADER>() as u32,
                    biWidth: bounds.w,
                    biHeight: bounds.h,
                    biPlanes: 1,
                    biBitCount: 32,
                    biCompression: BI_RGB,
                    ..std::mem::zeroed()
                },
                ..std::mem::zeroed()
            };
            let mut pixels = vec![0u8; (bounds.w * bounds.h * 4) as usize];
            SelectObject(buffer.dc, buffer.old);
            assert_eq!(
                GetDIBits(
                    buffer.dc,
                    buffer.bitmap,
                    0,
                    bounds.h as u32,
                    pixels.as_mut_ptr().cast(),
                    &mut info,
                    DIB_RGB_COLORS
                ),
                bounds.h
            );
            SelectObject(buffer.dc, buffer.bitmap);
            ReleaseDC(null_mut(), screen);
            assert!(
                pixels
                    .chunks_exact(4)
                    .filter(|p| p[..3] != [3, 2, 1])
                    .count()
                    > 5000
            );
            let mut bmp = Vec::new();
            bmp.extend_from_slice(b"BM");
            bmp.extend_from_slice(&(54u32 + pixels.len() as u32).to_le_bytes());
            bmp.extend_from_slice(&[0; 4]);
            bmp.extend_from_slice(&54u32.to_le_bytes());
            bmp.extend_from_slice(&40u32.to_le_bytes());
            bmp.extend_from_slice(&bounds.w.to_le_bytes());
            bmp.extend_from_slice(&bounds.h.to_le_bytes());
            bmp.extend_from_slice(&1u16.to_le_bytes());
            bmp.extend_from_slice(&32u16.to_le_bytes());
            bmp.extend_from_slice(&0u32.to_le_bytes());
            bmp.extend_from_slice(&(pixels.len() as u32).to_le_bytes());
            bmp.extend_from_slice(&[0; 16]);
            bmp.extend_from_slice(&pixels);
            let path =
                std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("target/overlay-qa.bmp");
            std::fs::write(path, bmp).unwrap();
        }
    }
}
