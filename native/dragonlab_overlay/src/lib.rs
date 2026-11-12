//! A passive Windows overlay. It never reads or sends game input.
use serde::Deserialize;
use std::{
    collections::BTreeMap,
    ffi::{c_char, CString},
    sync::{
        atomic::{AtomicU64, Ordering},
        Arc, Mutex, OnceLock,
    },
};

const MAX_INPUT: usize = 8 * 1024 * 1024;
const GREEN: u32 = 0x009cf577;
const OBSERVED: u32 = 0x00cbe6c1;
const ORANGE: u32 = 0x0077c4ff;
const MUTED: u32 = 0x00a0b39a;
const TEXT: u32 = 0x00eef7ec;
const BG: u32 = 0x00090d06;
const COLOR_KEY: u32 = 0x00030201;

#[derive(Clone, Deserialize, PartialEq, Default)]
#[serde(default)]
struct Style {
    color: String,
    observed_color: String,
    width: f64,
    font_size: f64,
}
#[derive(Clone, Deserialize, PartialEq, Default)]
#[serde(default)]
struct Player {
    x: f64,
    y: f64,
    hero: bool,
    selected: bool,
    label: String,
    dead: bool,
}
#[derive(Clone, Deserialize, PartialEq, Default)]
#[serde(default)]
struct Annotation {
    points: Vec<Option<[f64; 2]>>,
    color: String,
    width: f64,
    label: String,
    x: f64,
    y: f64,
}
#[derive(Clone, Deserialize, PartialEq)]
#[serde(default)]
struct Guide {
    bar: [f64; 4],
    power: Option<f64>,
    #[serde(rename = "maxPower")]
    max_power: f64,
    label: String,
    visible: bool,
    updating: bool,
    blocked: bool,
    measured: bool,
}
impl Default for Guide {
    fn default() -> Self {
        Self {
            bar: [0.; 4],
            power: None,
            max_power: 400.,
            label: String::new(),
            visible: false,
            updating: false,
            blocked: false,
            measured: false,
        }
    }
}
#[derive(Clone, Deserialize, PartialEq)]
#[serde(default)]
struct Scene {
    #[serde(rename = "box")]
    area: [f64; 4],
    viewport: [f64; 2],
    planned: Vec<Vec<Option<[f64; 2]>>>,
    observed: BTreeMap<String, Vec<Option<[f64; 2]>>>,
    players: Vec<Player>,
    annotations: Vec<Annotation>,
    visible: bool,
    style: Style,
    guide: Guide,
}
impl Default for Scene {
    fn default() -> Self {
        Self {
            area: [0.; 4],
            viewport: [800., 600.],
            planned: Vec::new(),
            observed: BTreeMap::new(),
            players: Vec::new(),
            annotations: Vec::new(),
            visible: false,
            style: Style::default(),
            guide: Guide::default(),
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq)]
struct Bounds {
    x: i32,
    y: i32,
    w: i32,
    h: i32,
}
impl Scene {
    fn valid(&self) -> bool {
        fn finite(x: f64) -> bool {
            x.is_finite() && x.abs() <= 2_000_000.
        }
        let points = self.planned.iter().chain(self.observed.values());
        if !self
            .area
            .iter()
            .chain(self.viewport.iter())
            .chain(self.guide.bar.iter())
            .all(|v| finite(*v))
            || self.viewport[0] <= 0.
            || self.viewport[1] <= 0.
        {
            return false;
        }
        if self.planned.len() > 512
            || self.observed.len() > 512
            || self.players.len() > 256
            || self.annotations.len() > 512
            || self.guide.label.chars().count() > 2048
        {
            return false;
        }
        if !self.guide.max_power.is_finite()
            || self.guide.max_power <= 0.
            || self.guide.power.is_some_and(|v| !v.is_finite())
        {
            return false;
        }
        let mut count = 0usize;
        for path in points {
            count += path.len();
            if count > 200_000 || !path.iter().flatten().flatten().all(|v| finite(*v)) {
                return false;
            }
        }
        if !self
            .players
            .iter()
            .all(|p| finite(p.x) && finite(p.y) && p.label.chars().count() <= 2048)
        {
            return false;
        }
        for a in &self.annotations {
            count += a.points.len();
            if count > 200_000
                || !finite(a.x)
                || !finite(a.y)
                || a.label.chars().count() > 2048
                || !a.points.iter().flatten().flatten().all(|v| finite(*v))
            {
                return false;
            }
        }
        self.bounds()
            .is_none_or(|b| b.w > 0 && b.h > 0 && b.w <= 16384 && b.h <= 16384)
    }
    fn field_height(&self) -> f64 {
        (self.area[3] - self.area[1]) * (516. / self.viewport[1]).min(1.)
    }
    fn bounds(&self) -> Option<Bounds> {
        let mut rectangle = None;
        if self.visible && self.area[2] > self.area[0] && self.area[3] > self.area[1] {
            rectangle = Some([
                self.area[0],
                self.area[1],
                self.area[2],
                self.area[1] + self.field_height(),
            ]);
        }
        if self.guide.visible {
            let [x1, y1, x2, y2] = self.guide.bar;
            let rect = [
                x1.min(x2) - 16.,
                y1.min(y2) - 54.,
                x1.max(x2) + 16.,
                y1.max(y2) + 20.,
            ];
            rectangle = Some(if let Some(r) = rectangle {
                [
                    r[0].min(rect[0]),
                    r[1].min(rect[1]),
                    r[2].max(rect[2]),
                    r[3].max(rect[3]),
                ]
            } else {
                rect
            });
        }
        rectangle.map(|r| {
            let x = r[0].floor() as i32;
            let y = r[1].floor() as i32;
            Bounds {
                x,
                y,
                w: (r[2].ceil() as i32 - x).max(1),
                h: (r[3].ceil() as i32 - y).max(1),
            }
        })
    }
}

fn color(value: &str, fallback: u32) -> u32 {
    if value.len() != 7 || !value.starts_with('#') {
        return fallback;
    }
    match u32::from_str_radix(&value[1..], 16) {
        Ok(v) => (v >> 16) | (v & 0x00ff00) | ((v & 0xff) << 16),
        Err(_) => fallback,
    }
}
fn stroke(value: f64, default: i32) -> i32 {
    if value.is_finite() && value > 0. {
        value.round().clamp(1., 12.) as i32
    } else {
        default
    }
}

#[derive(Default)]
struct Shared {
    pending: Mutex<Option<(u64, Scene)>>,
    submitted: AtomicU64,
    painted: AtomicU64,
    coalesced: AtomicU64,
}

#[cfg(windows)]
mod win;
#[cfg(windows)]
use win::Runtime;
#[cfg(not(windows))]
struct Runtime;
static RUNTIME: OnceLock<Mutex<Option<Runtime>>> = OnceLock::new();
fn runtime() -> &'static Mutex<Option<Runtime>> {
    RUNTIME.get_or_init(|| Mutex::new(None))
}

/// Returns 0 for an accepted latest scene, 1 for an unchanged scene, negative for error.
///
/// # Safety
/// `input` must refer to `len` readable bytes for the duration of this call.
#[no_mangle]
pub unsafe extern "C" fn dl_overlay_update_json(input: *const u8, len: usize) -> i32 {
    std::panic::catch_unwind(|| {
        if input.is_null() || len == 0 || len > MAX_INPUT {
            return -1;
        }
        let data = unsafe { std::slice::from_raw_parts(input, len) };
        let Ok(scene) = serde_json::from_slice::<Scene>(data) else {
            return -2;
        };
        if !scene.valid() {
            return -3;
        }
        #[cfg(windows)]
        {
            let Ok(mut slot) = runtime().lock() else {
                return -4;
            };
            if slot.is_none() {
                match Runtime::start() {
                    Ok(r) => *slot = Some(r),
                    Err(_) => return -5,
                }
            }
            slot.as_mut().unwrap().submit(scene)
        }
        #[cfg(not(windows))]
        {
            -6
        }
    })
    .unwrap_or(-9)
}

/// Stops and joins the overlay's message thread. May be called repeatedly.
#[no_mangle]
pub extern "C" fn dl_overlay_close() {
    let _ = std::panic::catch_unwind(|| {
        if let Ok(mut slot) = runtime().lock() {
            #[cfg(windows)]
            if let Some(mut worker) = slot.take() {
                worker.close()
            }
            #[cfg(not(windows))]
            {
                slot.take();
            }
        }
    });
}

/// Bit 0: message thread alive. Bit 1: passive window visible.
#[no_mangle]
pub extern "C" fn dl_overlay_status() -> u32 {
    std::panic::catch_unwind(|| {
        let Ok(slot) = runtime().lock() else { return 0 };
        #[cfg(windows)]
        {
            slot.as_ref().map_or(0, |r| r.flags())
        }
        #[cfg(not(windows))]
        {
            {
                let _ = &slot;
                0
            }
        }
    })
    .unwrap_or(0)
}

/// Read-only diagnostics; caller owns the returned UTF-8 string until `dl_overlay_string_free`.
#[no_mangle]
pub extern "C" fn dl_overlay_status_json() -> *mut c_char {
    std::panic::catch_unwind(|| {
        let value = if let Ok(slot) = runtime().lock() {
            #[cfg(windows)]
            {
                slot.as_ref()
                    .map(|r| r.status())
                    .unwrap_or(serde_json::json!({"running":false}))
            }
            #[cfg(not(windows))]
            {
                {
                    let _ = &slot;
                    serde_json::json!({"running":false,"unsupported":true})
                }
            }
        } else {
            serde_json::json!({"running":false,"error":"state lock"})
        };
        CString::new(value.to_string()).map_or(std::ptr::null_mut(), CString::into_raw)
    })
    .unwrap_or(std::ptr::null_mut())
}
#[no_mangle]
/// # Safety
/// `value` must be null or a live pointer returned by `dl_overlay_status_json`.
/// It must be freed exactly once and never accessed after this call.
pub unsafe extern "C" fn dl_overlay_string_free(value: *mut c_char) {
    if !value.is_null() {
        unsafe {
            drop(CString::from_raw(value));
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn keeps_exact_vertices_and_explicit_gaps() {
        let scene: Scene = serde_json::from_value(
            serde_json::json!({"box":[0,0,800,600],"planned":[[[1.,2.],null,[3.,4.]]]}),
        )
        .unwrap();
        assert_eq!(scene.planned[0], vec![Some([1., 2.]), None, Some([3., 4.])]);
        assert!(scene.valid());
    }
    #[test]
    fn guide_geometry_is_in_screen_coordinates() {
        let mut scene = Scene::default();
        scene.guide.visible = true;
        scene.guide.bar = [100., 700., 500., 710.];
        assert_eq!(
            scene.bounds(),
            Some(Bounds {
                x: 84,
                y: 646,
                w: 432,
                h: 84
            })
        );
        scene.visible = true;
        scene.area = [10., 20., 810., 620.];
        assert_eq!(
            scene.bounds(),
            Some(Bounds {
                x: 10,
                y: 20,
                w: 800,
                h: 710
            })
        );
    }
    #[test]
    fn rejects_huge_inputs_and_invalid_geometry() {
        let mut scene = Scene::default();
        assert!(scene.valid());
        scene.visible = true;
        scene.area = [0., 0., 20_000., 400.];
        assert!(!scene.valid());
        scene = Scene::default();
        scene.guide.max_power = 0.;
        assert!(!scene.valid());
        assert_eq!(unsafe { dl_overlay_update_json(std::ptr::null(), 1) }, -1);
    }
    #[test]
    fn colors_and_strokes_are_bounded() {
        assert_eq!(color("#77F59C", 0), GREEN);
        assert_eq!(color("oops", 3), 3);
        assert_eq!(stroke(100., 2), 12);
    }
}
