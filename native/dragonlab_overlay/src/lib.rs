//! A passive Windows overlay. It never reads or sends game input.
use serde::Deserialize;
use std::{
    collections::{BTreeMap, BTreeSet},
    ffi::{c_char, CString},
    sync::{
        atomic::{AtomicU64, Ordering},
        Arc, Mutex, OnceLock,
    },
};

const MAX_INPUT: usize = 8 * 1024 * 1024;
// One aggregate work budget instead of silently truncating an actor collection.
// Vertices cost one unit; an actor reserves its marker/leader/label operations.
const MAX_GEOMETRY_UNITS: usize = 200_000;
const ACTOR_UNITS: usize = 32;
const GREEN: u32 = 0x0000ffbb;
const OBSERVED: u32 = 0x00bbefe0;
const ORANGE: u32 = 0x0077c4ff;
const MUTED: u32 = 0x009c9c9c;
const CYAN: u32 = 0x00dbcb7b;
const TEXT: u32 = 0x00f3f5f5;
const BG: u32 = 0x00191919;
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
    role: Option<Role>,
    number: Option<i64>,
}
#[derive(Clone, Copy, Deserialize, PartialEq, Eq, Default, Debug)]
#[serde(rename_all = "lowercase")]
enum Role {
    Hero,
    Ally,
    Enemy,
    #[default]
    Unknown,
}
impl Player {
    fn role(&self) -> Role {
        self.role
            .unwrap_or(if self.hero { Role::Hero } else { Role::Unknown })
    }
    fn colour(&self) -> u32 {
        if self.selected {
            return ORANGE;
        }
        match self.role() {
            Role::Hero => GREEN,
            Role::Ally => CYAN,
            Role::Enemy => OBSERVED,
            Role::Unknown => MUTED,
        }
    }
    fn compact_label(&self, index: usize) -> String {
        let id = self
            .number
            .map_or_else(|| (index + 1).to_string(), |n| n.to_string());
        let role = match self.role() {
            Role::Hero => "TÚ",
            Role::Ally => "A",
            Role::Enemy => "E",
            Role::Unknown => "?",
        };
        format!("{}{role}{id}", if self.selected { "▶ " } else { "" })
    }
}

#[derive(Debug)]
struct ActorLabel {
    members: Vec<usize>,
    x: f64,
    y: f64,
    width: f64,
    colour: u32,
    value: String,
}

/// Pack labels into disjoint cells. A full field groups additional actors in
/// their preferred cell instead of dropping them or changing target order.
/// The free-cell set makes dense edge clusters O(actors * log(cells)).
fn actor_labels(scene: &Scene, width: f64, height: f64, font_size: i32) -> Vec<ActorLabel> {
    if width <= 0. || height <= 0. {
        return Vec::new();
    }
    let padding = 6_f64.min(width / 4.).min(height / 4.);
    let header = (height * 0.15).min(58.);
    let cell_height = (font_size as f64 + 10.).max(20.);
    let cell_width = (font_size as f64 * 8. + 16.).clamp(64., 144.);
    let columns = (((width - 2. * padding) / cell_width).floor() as usize).max(1);
    let rows = (((height - header - 2. * padding) / cell_height).floor() as usize).max(1);
    let actual_width = (width - 2. * padding) / columns as f64;
    let actual_height = (height - header - 2. * padding) / rows as f64;
    let mut free: BTreeSet<usize> = (0..columns * rows).collect();
    let mut cells: BTreeMap<usize, Vec<usize>> = BTreeMap::new();
    let alive = scene.players.iter().filter(|p| !p.dead).count();
    for (index, player) in scene.players.iter().enumerate().filter(|(_, p)| !p.dead) {
        let x = player.x * width / scene.viewport[0];
        let y = player.y * (scene.area[3] - scene.area[1]) / scene.viewport[1] - 23.;
        let column = (((x - padding) / actual_width).floor().max(0.) as usize).min(columns - 1);
        let row = (((y - header - padding) / actual_height).floor().max(0.) as usize).min(rows - 1);
        let preferred = row * columns + column;
        let cell = free
            .range(preferred..)
            .next()
            .or_else(|| free.first())
            .copied()
            .unwrap_or(preferred);
        free.remove(&cell);
        cells.entry(cell).or_default().push(index);
    }
    cells
        .into_iter()
        .map(|(cell, mut members)| {
            // A selected actor remains visible in a grouped label.
            members.sort_by_key(|index| !scene.players[*index].selected);
            let player = &scene.players[members[0]];
            let value = if members.len() > 1 {
                format!(
                    "{} · +{}",
                    player.compact_label(members[0]),
                    members.len() - 1
                )
            } else if alive > 6 || player.label.is_empty() {
                player.compact_label(members[0])
            } else {
                player.label.clone()
            };
            ActorLabel {
                x: padding + (cell % columns) as f64 * actual_width,
                y: header + padding + (cell / columns) as f64 * actual_height + actual_height / 2.,
                width: actual_width,
                colour: player.colour(),
                members,
                value,
            }
        })
        .collect()
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
    font_size: f64,
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
            font_size: 12.,
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
            || self.annotations.len() > 512
            || self.guide.label.chars().count() > 2048
        {
            return false;
        }
        if !self.guide.max_power.is_finite()
            || self.guide.max_power <= 0.
            || self.guide.power.is_some_and(|v| !v.is_finite())
            || !self.guide.font_size.is_finite()
        {
            return false;
        }
        let mut count = self.guide.label.chars().count();
        // checked_add also makes this safe on 32-bit hosts. There is no player
        // count cap; all actors fit or the entire proposed scene is rejected.
        for player in &self.players {
            let cost = ACTOR_UNITS + player.label.chars().count();
            let Some(next) = count.checked_add(cost) else {
                return false;
            };
            count = next;
            if count > MAX_GEOMETRY_UNITS {
                return false;
            }
        }
        for path in points {
            count += path.len();
            if count > MAX_GEOMETRY_UNITS || !path.iter().flatten().flatten().all(|v| finite(*v)) {
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
            count += a.points.len() + a.label.chars().count() + 8;
            if count > MAX_GEOMETRY_UNITS
                || !finite(a.x)
                || !finite(a.y)
                || a.label.chars().count() > 2048
                || !a.points.iter().flatten().flatten().all(|v| finite(*v))
            {
                return false;
            }
        }
        self.bounds().is_none_or(|b| {
            b.w > 0
                && b.h > 0
                && b.w <= 16384
                && b.h <= 16384
                && (b.w as u64) * (b.h as u64) <= 32_000_000
        })
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
                y1.min(y2) - 38.,
                x1.max(x2) + 16.,
                y1.max(y2) + 8.,
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
    presentations: AtomicU64,
    geometry_updates: AtomicU64,
    shows: AtomicU64,
    hides: AtomicU64,
    presentation_errors: AtomicU64,
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
                y: 662,
                w: 432,
                h: 56
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
                h: 698
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
        assert_eq!(color("#BBFF00", 0), GREEN);
        assert_eq!(color("oops", 3), 3);
        assert_eq!(stroke(100., 2), 12);
    }
    #[test]
    fn actor_roles_are_distinct_and_legacy_nonheroes_are_unknown() {
        let hero = Player {
            hero: true,
            ..Player::default()
        };
        let ally = Player {
            role: Some(Role::Ally),
            ..Player::default()
        };
        let enemy = Player {
            role: Some(Role::Enemy),
            ..Player::default()
        };
        assert_eq!(hero.role(), Role::Hero);
        assert_eq!(Player::default().role(), Role::Unknown);
        assert_ne!(hero.colour(), ally.colour());
        assert_ne!(ally.colour(), enemy.colour());
    }
    #[test]
    fn crowded_labels_preserve_every_actor_without_overlaps_or_an_actor_cap() {
        for count in [8, 12, 16, 32, 300] {
            let scene = Scene {
                area: [0., 0., 800., 600.],
                visible: true,
                players: (0..count)
                    .map(|i| Player {
                        x: 1500.,
                        y: 400.,
                        number: Some(i as i64 + 1),
                        role: Some(Role::Enemy),
                        selected: i == count - 1,
                        ..Player::default()
                    })
                    .collect(),
                ..Scene::default()
            };
            assert!(scene.valid());
            let labels = actor_labels(&scene, 800., scene.field_height(), 12);
            let members: BTreeSet<usize> = labels
                .iter()
                .flat_map(|l| l.members.iter().copied())
                .collect();
            assert_eq!(members.len(), count);
            assert!(labels.iter().any(|label| label.value.starts_with('▶')));
            for (index, label) in labels.iter().enumerate() {
                for other in labels.iter().skip(index + 1) {
                    assert!(
                        (label.y - other.y).abs() >= 20.
                            || label.x + label.width <= other.x + 0.01
                            || other.x + other.width <= label.x + 0.01
                    );
                }
            }
        }
    }
}
