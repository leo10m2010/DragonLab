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
const CLASS: &str = "DragonLab.Native.PassiveOverlay.019";

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
        if self.thread.as_ref().is_none_or(|h| h.is_finished()) {
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
                "transparent":style&WS_EX_TRANSPARENT!=0,"no_activate":style&WS_EX_NOACTIVATE!=0,"layered":style&WS_EX_LAYERED!=0,
                "box":[rectangle.left,rectangle.top,rectangle.right,rectangle.bottom]})
        }
    }
    pub fn flags(&self) -> u32 {
        u32::from(self.thread.as_ref().is_some_and(|t| !t.is_finished()))
            | (u32::from(unsafe { IsWindowVisible(self.hwnd as HWND) } != 0) << 1)
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
    if SetLayeredWindowAttributes(hwnd, COLOR_KEY, 255, LWA_COLORKEY) == 0 {
        let error = GetLastError();
        DestroyWindow(hwnd);
        let _ = ready.send(Err(format!("SetLayeredWindowAttributes: {error}")));
        UnregisterClassW(name.as_ptr(), instance);
        return;
    }
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
                    if state.bounds != Some(bounds) {
                        SetWindowPos(
                            hwnd,
                            HWND_TOPMOST,
                            bounds.x,
                            bounds.y,
                            bounds.w,
                            bounds.h,
                            SWP_NOACTIVATE | SWP_NOOWNERZORDER,
                        );
                        state.bounds = Some(bounds);
                    }
                    ShowWindow(hwnd, SW_SHOWNOACTIVATE);
                    InvalidateRect(hwnd, null(), 0);
                    UpdateWindow(hwnd);
                } else {
                    ShowWindow(hwnd, SW_HIDE);
                    state.shared.painted.store(seq, Ordering::Release);
                }
            }
            return 0;
        }
        if msg == WM_PAINT {
            state.paint(hwnd);
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
}
impl WindowState {
    unsafe fn new(shared: Arc<Shared>) -> Self {
        Self {
            shared,
            scene: None,
            sequence: 0,
            bounds: None,
            buffer: None,
            font: make_font(16),
            font_size: 16,
            guide_font: make_font(18),
        }
    }
    unsafe fn paint(&mut self, hwnd: HWND) {
        let mut ps = std::mem::zeroed::<PAINTSTRUCT>();
        let target = BeginPaint(hwnd, &mut ps);
        if !target.is_null() {
            if let (Some(bounds), Some(scene)) = (self.bounds, self.scene.as_ref()) {
                if self
                    .buffer
                    .as_ref()
                    .is_none_or(|b| b.w != bounds.w || b.h != bounds.h)
                {
                    self.buffer = Buffer::new(target, bounds.w, bounds.h);
                }
                let font_size = if scene.style.font_size.is_finite() && scene.style.font_size > 0. {
                    (scene.style.font_size * 1.333).round().clamp(10., 36.) as i32
                } else {
                    16
                };
                if font_size != self.font_size {
                    DeleteObject(self.font);
                    self.font = make_font(font_size);
                    self.font_size = font_size;
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
                    BitBlt(target, 0, 0, bounds.w, bounds.h, dc, 0, 0, SRCCOPY);
                    self.shared.painted.store(self.sequence, Ordering::Release);
                }
            }
        }
        EndPaint(hwnd, &ps);
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
    if value.is_empty() {
        return;
    }
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
    let left = (x.round() as i32 - actual / 2).clamp(4, (width - actual - 8).max(4));
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
        let colour = if player.hero {
            GREEN
        } else if player.selected {
            ORANGE
        } else {
            OBSERVED
        };
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
        let value = if outside {
            format!("{} · fuera de vista", player.label)
        } else {
            player.label.clone()
        };
        text(
            dc,
            x,
            y + if outside { 15. } else { -23. },
            &value,
            colour,
            font,
            b.w,
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
            2,
        );
        line(dc, &[point(x, y - 22.), point(x, y + 12.)], colour, 3);
        line(
            dc,
            &[
                point(x - 7., y - 24.),
                point(x, y - 15.),
                point(x + 7., y - 24.),
                point(x - 7., y - 24.),
            ],
            colour,
            3,
        );
        if label.is_empty() {
            label = format!(
                "{} {power:.0} / {:.0} · {:.1}%",
                if guide.updating {
                    "ACTUALIZANDO"
                } else if guide.blocked {
                    "TERRENO BLOQUEA"
                } else {
                    "SUELTA EN"
                },
                guide.max_power,
                fraction * 100.
            );
        }
    } else if label.is_empty() {
        label = if guide.updating {
            "Calculando fuerza…"
        } else {
            "Sin potencia válida · revisa DragonLab"
        }
        .into();
    }
    text(
        dc,
        (x1 + x2) / 2. - ox,
        y1.min(y2) - 35. - oy,
        &label,
        if guide.power.is_some() { colour } else { MUTED },
        font,
        b.w,
    );
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn latest_scene_is_painted_without_focus_or_input() {
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
    fn exports_only_own_offscreen_render_for_visual_qa() {
        // This renders synthetic geometry into a private compatible bitmap.
        // No desktop pixels, app windows or screen captures are read.
        unsafe {
            let scene:Scene=serde_json::from_value(serde_json::json!({
                "box":[0,0,900,640],"viewport":[900,640],"visible":true,
                "style":{"color":"#77F59C","width":3},
                "planned":[(0..=120).map(|i|{let t=i as f64/2.;Some([100.+10.*t,400.-0.25*t*(60.-t)])}).collect::<Vec<_>>()],
                "observed":{"fixture":(0..=60).map(|i|{let t=i as f64;Some([100.+10.*t,405.-0.24*t*(60.-t)])}).collect::<Vec<_>>()},
                "players":[{"x":100,"y":400,"hero":true,"label":"TÚ"},{"x":700,"y":400,"selected":true,"label":"▶ ENEMIGO 1"},{"x":1100,"y":300,"label":"2"}],
                "annotations":[{"points":[[450,0],[450,516]],"color":"#D69CFC","width":1,"label":"Mirror","x":450,"y":43},{"points":[[650,0],[650,516]],"color":"#7BCDDB","width":1,"label":"Tornado","x":650,"y":43}],
                "guide":{"visible":true,"bar":[80,610,820,610],"power":205,"maxPower":400,"label":"Armor · SUELTA EN 205 / 400 · 51.2%","measured":true}
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
            let font = make_font(16);
            let guide_font = make_font(18);
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
