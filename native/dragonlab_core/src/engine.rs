//! Independent port of DragonLab's single-projectile ballistic search.
//!
//! Unsupported projectile families deliberately return to the checked Python
//! implementation. Nothing here assigns new calibration values to a vehicle.
use serde_json::{json, Value};
use std::collections::{HashMap, HashSet};
use std::sync::atomic::{AtomicBool, Ordering};

const EPS: f64 = 1e-7;
type Point = [f64; 3];

fn check(cancel: &AtomicBool) -> Result<(), String> {
    if cancel.load(Ordering::Relaxed) {
        Err("cancelled".into())
    } else {
        Ok(())
    }
}
fn unsupported(why: &str) -> String {
    format!("unsupported: {why}")
}
fn number(v: &Value, key: &str, default: f64) -> Result<f64, String> {
    match v.get(key) {
        None => Ok(default),
        Some(value) => value
            .as_f64()
            .filter(|n| n.is_finite())
            .ok_or_else(|| format!("invalid number: {key}")),
    }
}
fn n(v: &Value, key: &str, default: f64) -> f64 {
    v.get(key).and_then(Value::as_f64).unwrap_or(default)
}
fn truth(v: &Value) -> bool {
    match v {
        Value::Null => false,
        Value::Bool(b) => *b,
        Value::Number(v) => v.as_f64().unwrap_or(0.0) != 0.0,
        Value::String(s) => !s.is_empty(),
        Value::Array(a) => !a.is_empty(),
        Value::Object(o) => !o.is_empty(),
    }
}
fn flag(v: &Value, key: &str, default: bool) -> bool {
    v.get(key).map(truth).unwrap_or(default)
}
fn weather_kind(w: &Value) -> Option<u8> {
    let kind = w
        .get("resolvedTypeId")
        .filter(|x| !x.is_null())
        .or_else(|| w.get("typeId"))
        .or_else(|| w.get("type"))
        .or_else(|| w.get("name"));
    match (kind.and_then(Value::as_f64), kind.and_then(Value::as_str)) {
        (Some(7.0), _) | (_, Some("Mirror" | "MIRROR" | "mirror")) => Some(7),
        (Some(8.0), _) | (_, Some("Tornado" | "TORNADO" | "tornado")) => Some(8),
        _ => None,
    }
}
fn validate_environment(env: &Value) -> Result<(), String> {
    // Do not reinterpret malformed optional geometry as zero/default values.
    // The adapter can hand these inputs to its existing validation/error path.
    for key in ["originY", "mapHeight", "nativeEulerStep", "hitTolerance"] {
        if env.get(key).is_some_and(|x| x.as_f64().is_none()) {
            return Err(unsupported("non-numeric environment field"));
        }
    }
    if let Some(terrain) = env.get("terrain") {
        for key in ["originX", "originY", "width", "height"] {
            if terrain.get(key).is_some_and(|x| x.as_f64().is_none()) {
                return Err(unsupported("non-numeric terrain geometry"));
            }
        }
        for key in ["width", "height"] {
            let dimension = n(terrain, key, 0.0);
            if dimension < 0.0 || dimension.fract() != 0.0 || dimension > 1_000_000.0 {
                return Err(unsupported("terrain dimensions"));
            }
        }
        if let Some(heights) = terrain.get("heights") {
            if !heights
                .as_array()
                .is_some_and(|a| a.iter().all(|v| v.is_null() || v.as_f64().is_some()))
            {
                return Err(unsupported("height profile"));
            }
        }
        if let Some(polygon) = terrain.get("polygon") {
            if !polygon.as_array().is_some_and(|a| {
                a.iter().all(|p| {
                    p.as_array()
                        .is_some_and(|xy| xy.len() == 2 && xy.iter().all(|v| v.as_f64().is_some()))
                })
            }) {
                return Err(unsupported("polygon geometry"));
            }
        }
        for key in ["rows", "runs"] {
            if let Some(rows) = terrain.get(key) {
                if !rows.as_array().is_some_and(|a| {
                    a.iter().all(|row| {
                        row.as_array()
                            .is_some_and(|r| r.iter().all(|v| v.as_f64().is_some()))
                    })
                }) {
                    return Err(unsupported("terrain rows"));
                }
            }
        }
        for key in ["pixels", "mask"] {
            if terrain.get(key).is_some_and(|x| !x.is_array()) {
                return Err(unsupported("terrain mask"));
            }
        }
    }
    if let Some(list) = env
        .get("activeWeathers")
        .or_else(|| env.get("weathers"))
        .and_then(Value::as_array)
    {
        for w in list {
            if weather_kind(w).is_some() && w.get("x").and_then(Value::as_f64).is_none() {
                return Err(unsupported("weather position"));
            }
            if w.get("size").is_some_and(|x| x.as_f64().is_none()) {
                return Err(unsupported("weather width"));
            }
        }
    }
    Ok(())
}
fn rounded(value: f64, digits: usize) -> f64 {
    // Formatting rounds the represented binary value, as Python round(x, n)
    // does; multiplying by 10^n first would change values near decimal ties.
    format!("{value:.digits$}").parse().unwrap_or(value)
}
fn profile(mobile: &str) -> Option<(f64, f64)> {
    Some(match mobile {
        "ARMOR" | "RANDOMIZER" => (52.0, 33.0),
        "ICE" => (58.0, 50.0),
        "ADUKA" | "KNIGHT" | "NAK" => (130.0, 40.0),
        "LIGHTNING" => (58.0, 44.0),
        "BIGFOOT" | "DRAGON" | "DRAGON2" | "KALSIDDON" => (58.0, 50.0),
        "JD" => (68.0, 45.0),
        "ASATE" => (40.0, 30.0),
        "FOX" => (30.0, 44.0),
        "BOOMER" => (70.0, 30.0),
        "GRUB" => (54.0, 33.0),
        "FROG" => (52.0, 33.0),
        "RANDOM" | "TRICO" | "MAGE" | "TURTLE" | "ELECTRICO" | "RAON" => (51.0, 51.0),
        _ => return None,
    })
}
#[derive(Clone)]
struct Settings {
    mobile: String,
    angle: f64,
    wind: f64,
    wind_angle: f64,
    hero_x: f64,
    hero_y: f64,
    target_x: f64,
    target_y: f64,
    gravity: f64,
    wind_scale: f64,
    wind_mode: String,
    power_scale: f64,
    body_angle: f64,
    muzzle: bool,
    look: bool,
    weather: String,
    shot: u64,
    env: Value,
    max_time: f64,
    max_power: f64,
    speed_offset: f64,
    angle_offset: f64,
    quantize: bool,
    launch_offset: Option<[f64; 2]>,
    backshot: bool,
}
impl Settings {
    fn parse(v: &Value) -> Result<Self, String> {
        if !v.is_object() {
            return Err("settings must be an object".into());
        }
        let mobile = v
            .get("mobile")
            .and_then(Value::as_str)
            .unwrap_or("ARMOR")
            .to_owned();
        if profile(&mobile).is_none() {
            return Err("Vehículo desconocido".into());
        }
        // NAK and Kalsiddon have continuations; volleys have distinct scoring.
        if matches!(
            mobile.as_str(),
            "NAK" | "KALSIDDON" | "BIGFOOT" | "DRAGON" | "RANDOMIZER"
        ) {
            return Err(unsupported("projectile family"));
        }
        let shot = v
            .get("selected_shot")
            .map(|x| {
                x.as_u64()
                    .filter(|x| *x <= 2)
                    .ok_or("invalid selected_shot")
            })
            .transpose()?
            .unwrap_or(0);
        if shot == 1
            && matches!(
                mobile.as_str(),
                "GRUB" | "MAGE" | "TURTLE" | "TRICO" | "BOOMER"
            )
        {
            return Err(unsupported("multiple or wave projectiles"));
        }
        let env = v.get("environment").cloned().unwrap_or(json!({}));
        if !env.is_object() {
            return Err("El entorno debe ser un objeto JSON".into());
        }
        if env.get("weatherModel").and_then(Value::as_str) == Some("gunbound-world") {
            return Err(unsupported("GunBound World"));
        }
        if env.get("projectiles").map(truth).unwrap_or(false) {
            return Err(unsupported("custom projectiles"));
        }
        if env.get("terrain").is_some_and(|x| !x.is_object()) {
            return Err("El terreno debe ser un objeto".into());
        }
        if env.get("activeWeathers").is_some_and(|x| !x.is_array()) {
            return Err("activeWeathers debe ser una lista".into());
        }
        validate_environment(&env)?;
        let offset = match v.get("launch_offset") {
            None | Some(Value::Null) => None,
            Some(Value::Array(a)) if a.len() == 2 => Some([
                a[0].as_f64().ok_or("invalid launch_offset")?,
                a[1].as_f64().ok_or("invalid launch_offset")?,
            ]),
            _ => return Err("Desplazamiento del cañón inválido".into()),
        };
        let s = Self {
            mobile,
            angle: number(v, "angle", 46.0)?,
            wind: number(v, "wind", 0.0)?,
            wind_angle: number(v, "wind_angle", 90.0)?,
            hero_x: number(v, "hero_x", 130.0)?,
            hero_y: number(v, "hero_y", 430.0)?,
            target_x: number(v, "target_x", 670.0)?,
            target_y: number(v, "target_y", 420.0)?,
            gravity: number(v, "gravity", 73.5)?,
            wind_scale: number(v, "wind_scale", 0.74)?,
            wind_mode: v
                .get("wind_mode")
                .and_then(Value::as_str)
                .unwrap_or("smooth")
                .into(),
            power_scale: number(v, "power_scale", 1.0)?,
            body_angle: number(v, "body_angle", 0.0)?,
            muzzle: flag(v, "muzzle", true),
            look: flag(v, "look", true),
            weather: v
                .get("weather")
                .and_then(Value::as_str)
                .unwrap_or("Normal")
                .into(),
            shot,
            env,
            max_time: number(v, "max_time", 20.0)?,
            max_power: number(v, "max_power", 400.0)?,
            speed_offset: number(v, "speed_offset", 0.0)?,
            angle_offset: number(v, "angle_offset", 0.0)?,
            quantize: flag(v, "quantize_power", false),
            launch_offset: offset,
            backshot: flag(v, "is_backshot", false),
        };
        if !(-180.0..=180.0).contains(&s.angle) {
            return Err("El ángulo debe estar entre -180 y 180 grados".into());
        }
        if !(0.0..=100.0).contains(&s.wind) {
            return Err("Viento fuera de rango (0–100)".into());
        }
        if s.gravity <= 0.0 || s.power_scale <= 0.0 || s.wind_scale < 0.0 {
            return Err("Calibración inválida".into());
        }
        if s.max_time <= 0.0 || s.max_time > 60.0 || s.max_power <= 0.0 || s.max_power > 2000.0 {
            return Err("Límites de simulación o disparo inválidos".into());
        }
        if !matches!(s.wind_mode.as_str(), "smooth" | "floor") {
            return Err("Modelo de viento desconocido".into());
        }
        Ok(s)
    }
    fn origin(&self) -> (f64, f64, f64) {
        let side = if self.look { 1.0 } else { -1.0 };
        let (mut x, mut y) = (self.hero_x, self.hero_y);
        if let Some(offset) = self.launch_offset {
            return (x + offset[0], y + offset[1], side);
        }
        if self.muzzle {
            let (mut offset, mut radius) = profile(&self.mobile).unwrap();
            if self.mobile == "ICE" && self.shot > 0 {
                offset = 40.0;
                radius = 40.0;
            }
            let face = if self.mobile == "ADUKA" { -side } else { side };
            let a =
                ((if face > 0.0 { offset } else { 180.0 - offset }) - self.body_angle).to_radians();
            x += (a.cos() * radius).round_ties_even();
            y -= (a.sin() * radius).round_ties_even();
        }
        (x, y, side)
    }
    fn acceleration(&self) -> (f64, f64) {
        if let Some(a) = self
            .env
            .get("observedAcceleration")
            .and_then(Value::as_array)
        {
            if a.len() == 2 {
                if let (Some(x), Some(y)) = (a[0].as_f64(), a[1].as_f64()) {
                    return (x, y);
                }
            }
        }
        let a = self.wind_angle.rem_euclid(360.0).to_radians();
        let (mut x, mut y) = (self.wind * a.cos(), self.wind * a.sin());
        if self.wind_mode == "floor" {
            x = x.floor();
            y = y.floor();
        }
        (self.wind_scale * x, self.gravity - self.wind_scale * y)
    }
    fn speed(&self, power: f64) -> f64 {
        let speed = (power * self.power_scale + self.speed_offset).max(0.0);
        if self.quantize {
            speed.trunc()
        } else {
            speed
        }
    }
    fn approximate(&self) -> bool {
        matches!(
            self.mobile.as_str(),
            "BOOMER" | "TRICO" | "TURTLE" | "KNIGHT" | "FROG" | "LIGHTNING"
        )
    }
}

fn roots(a: f64, b: f64, c: f64) -> Vec<f64> {
    if a.abs() < EPS {
        return if b.abs() < EPS { vec![] } else { vec![-c / b] };
    }
    let d = b * b - 4.0 * a * c;
    if d < 0.0 {
        return vec![];
    }
    let q = d.sqrt();
    vec![(-b - q) / (2.0 * a), (-b + q) / (2.0 * a)]
}
fn crossing(x: f64, v: f64, a: f64, bound: f64, direction: f64, horizon: f64) -> Option<f64> {
    roots(a / 2.0, v, x - bound)
        .into_iter()
        .filter(|t| EPS < *t && *t <= horizon && (v + a * t) * direction > EPS)
        .min_by(f64::total_cmp)
}
#[derive(Clone, Copy)]
struct Segment {
    start: f64,
    end: f64,
    x: f64,
    y: f64,
    vx: f64,
    vy: f64,
    ax: f64,
    ay: f64,
}
impl Segment {
    fn at(&self, time: f64) -> (f64, f64) {
        let dt = (time.min(self.end) - self.start).max(0.0);
        (
            self.x + self.vx * dt + self.ax * dt * dt / 2.0,
            self.y + self.vy * dt + self.ay * dt * dt / 2.0,
        )
    }
}
fn weather(env: &Value) -> (Vec<(f64, f64)>, Vec<f64>) {
    let mut tornado = vec![];
    let mut mirrors = vec![];
    if let Some(list) = env
        .get("activeWeathers")
        .or_else(|| env.get("weathers"))
        .and_then(Value::as_array)
    {
        for w in list {
            let code = weather_kind(w);
            if code == Some(8) {
                if n(w, "size", 0.0) > 0.0 {
                    tornado.push((n(w, "x", 0.0), (n(w, "size", 0.0) * 0.25).max(1.0)));
                }
            } else if code == Some(7) {
                mirrors.push(n(w, "x", 0.0));
            }
        }
    }
    tornado.sort_by(|a, b| a.0.total_cmp(&b.0).then(a.1.total_cmp(&b.1)));
    tornado.dedup();
    mirrors.sort_by(f64::total_cmp);
    mirrors.dedup();
    (tornado, mirrors)
}
fn segments(
    s: &Settings,
    power: f64,
    cancel: &AtomicBool,
) -> Result<(Vec<Segment>, Vec<Value>), String> {
    check(cancel)?;
    let (mut x, mut y, side) = s.origin();
    let origin = x;
    let angle = (s.angle + s.angle_offset).to_radians();
    let speed = s.speed(power);
    let (mut vx, mut vy) = (side * angle.cos() * speed, -angle.sin() * speed);
    let (mut ax, mut ay) = s.acceleration();
    let base = (ax, ay);
    let native_step = n(&s.env, "nativeEulerStep", 0.0);
    if native_step != 0.0 {
        vx -= ax * native_step / 2.0;
        vy -= ay * native_step / 2.0;
    }
    let (tornado, mirrors) = weather(&s.env);
    let mut entered = HashSet::new();
    let mut active: Option<(usize, f64, u8)> = None;
    let mut clock = 0.0;
    let mut result = vec![];
    let mut events = vec![];
    for _ in 0..8
        .max(tornado.len() * 5 + 4)
        .max(if mirrors.is_empty() { 0 } else { 64 })
    {
        check(cancel)?;
        let remaining = s.max_time - clock;
        if remaining <= EPS {
            break;
        }
        let mut dt = remaining;
        let mut event = "end";
        let mut entry = None;
        if let Some((i, entry_side, phase)) = active {
            let (center, width) = tornado[i];
            let edge = center
                + (if phase == 0 || phase == 2 {
                    -entry_side
                } else {
                    entry_side
                }) * width;
            let hit = if vx.abs() > EPS {
                (edge - x) / vx
            } else {
                f64::INFINITY
            };
            if EPS < hit && hit <= remaining {
                let quant = (((clock + hit - EPS) / 0.025).ceil() * 0.025 - clock).max(0.0);
                if quant <= dt {
                    dt = quant;
                    event = "bounce";
                }
            }
        } else {
            for (i, (center, width)) in tornado.iter().copied().enumerate() {
                if entered.contains(&i) {
                    continue;
                }
                let (lo, hi) = (center - width, center + width);
                let side_enter = if x < lo { -1.0 } else { 1.0 };
                let (hit, side_enter) = if lo - EPS <= x && x <= hi + EPS {
                    let velocity = if vx.abs() > EPS { vx } else { ax };
                    if velocity.abs() <= EPS {
                        continue;
                    }
                    (Some(0.0), if velocity > 0.0 { -1.0 } else { 1.0 })
                } else {
                    (
                        crossing(
                            x,
                            vx,
                            ax,
                            if x < lo { lo } else { hi },
                            -side_enter,
                            remaining,
                        ),
                        side_enter,
                    )
                };
                if let Some(hit) = hit {
                    let quant = (((clock + hit - EPS) / 0.025).ceil() * 0.025 - clock).max(0.0);
                    if quant <= dt {
                        dt = quant;
                        event = "enter";
                        entry = Some((i, side_enter, 0));
                    }
                }
            }
        }
        let top = n(&s.env, "originY", 0.0) - 600.0;
        for center in &mirrors {
            let faces = if (origin - center).abs() < 25.0 {
                [(*center, 1.0), (*center, -1.0)]
            } else {
                [(*center - 25.0, 1.0), (*center + 25.0, -1.0)]
            };
            for (edge, direction) in faces {
                if let Some(hit) = crossing(x, vx, ax, edge, direction, remaining) {
                    if y + vy * hit + ay * hit * hit / 2.0 >= top && hit < dt {
                        dt = hit;
                        event = "mirror";
                    }
                }
            }
            if (origin - center).abs() >= 25.0 && y < top {
                if let Some(hit) = crossing(y, vy, ay, top, 1.0, remaining) {
                    if (x + vx * hit + ax * hit * hit / 2.0 - center).abs() < 25.0 && hit < dt {
                        dt = hit;
                        event = "mirror";
                    }
                }
            }
        }
        let terrain = s.env.get("terrain").unwrap_or(&Value::Null);
        let origin_y = n(terrain, "originY", n(&s.env, "originY", 0.0));
        let height = n(
            terrain,
            "height",
            terrain
                .get("heights")
                .and_then(Value::as_array)
                .map_or(0.0, |a| a.len() as f64),
        );
        let map_height = if height != 0.0 {
            height
        } else {
            n(&s.env, "mapHeight", 1200.0)
        };
        let floor = (origin_y + map_height).max(s.hero_y).max(s.target_y) + 160.0;
        if let Some(hit) = crossing(y, vy, ay, floor, 1.0, remaining) {
            if hit <= dt {
                dt = hit;
                event = "end";
            }
        }
        let segment = Segment {
            start: clock,
            end: clock + dt,
            x,
            y,
            vx,
            vy,
            ax,
            ay,
        };
        if dt > EPS {
            result.push(segment);
            (x, y) = segment.at(clock + dt);
            vx += ax * dt;
            vy += ay * dt;
            clock += dt;
        }
        if event == "end" {
            break;
        }
        events.push(json!({"kind":event,"time":clock,"x":x,"y":y}));
        match event {
            "mirror" => vx = -vx,
            "enter" => {
                active = entry;
                ax = 0.0;
                ay = 0.0;
            }
            "bounce" => {
                let (i, entry_side, phase) = active.unwrap();
                if phase < 2 {
                    let rewind = (dt - 0.025).max(0.0);
                    (x, y) = segment.at(segment.start + rewind);
                    vx = -(segment.vx + segment.ax * rewind);
                    vy = segment.vy + segment.ay * rewind;
                    active = Some((i, entry_side, phase + 1));
                } else {
                    entered.insert(i);
                    active = None;
                    (ax, ay) = base;
                }
            }
            _ => {}
        }
    }
    Ok((result, events))
}
fn solid(terrain: &Value, mut x: f64, mut y: f64) -> bool {
    x -= n(terrain, "originX", 0.0);
    y -= n(terrain, "originY", 0.0);
    if let Some(heights) = terrain.get("heights").and_then(Value::as_array) {
        let index = x.round_ties_even() as i64;
        return index >= 0
            && (index as usize) < heights.len()
            && heights[index as usize]
                .as_f64()
                .is_some_and(|height| y >= height);
    }
    if let Some(polygon) = terrain
        .get("polygon")
        .and_then(Value::as_array)
        .filter(|p| !p.is_empty())
    {
        let mut inside = false;
        let mut previous = polygon.last().unwrap();
        for current in polygon {
            let (x1, y1) = (
                previous[0].as_f64().unwrap_or(0.0),
                previous[1].as_f64().unwrap_or(0.0),
            );
            let (x2, y2) = (
                current[0].as_f64().unwrap_or(0.0),
                current[1].as_f64().unwrap_or(0.0),
            );
            if (y1 > y) != (y2 > y) && x < (x2 - x1) * (y - y1) / (y2 - y1) + x1 {
                inside = !inside;
            }
            previous = current;
        }
        return inside;
    }
    let (ix, iy) = (x.round_ties_even() as i64, y.round_ties_even() as i64);
    let (width, height) = (
        n(terrain, "width", 0.0) as i64,
        n(terrain, "height", 0.0) as i64,
    );
    if ix < 0 || iy < 0 || ix >= width || iy >= height {
        return false;
    }
    if let Some(bitmap) = terrain
        .get("pixels")
        .or_else(|| terrain.get("mask"))
        .and_then(Value::as_array)
    {
        return bitmap
            .get((iy * width + ix) as usize)
            .map(truth)
            .unwrap_or(false);
    }
    if let Some(rows) = terrain
        .get("rows")
        .or_else(|| terrain.get("runs"))
        .and_then(Value::as_array)
    {
        if let Some(row) = rows.get(iy as usize).and_then(Value::as_array) {
            if flag(terrain, "rowsSorted", false) {
                return row.partition_point(|v| v.as_f64().unwrap_or(0.0) <= ix as f64) % 2 == 1;
            }
            return row.chunks_exact(2).any(|pair| {
                pair[0].as_f64().unwrap_or(0.0) <= ix as f64
                    && (ix as f64) < pair[1].as_f64().unwrap_or(0.0)
            });
        }
    }
    false
}
fn swept(
    terrain: &Value,
    a: Point,
    b: Point,
    cancel: &AtomicBool,
) -> Result<Option<Point>, String> {
    check(cancel)?;
    let (ox, oy) = (n(terrain, "originX", 0.0), n(terrain, "originY", 0.0));
    let height = n(terrain, "height", 0.0);
    let width = n(terrain, "width", 0.0);
    if height != 0.0 && (a[1].max(b[1]) < oy - 0.5 || a[1].min(b[1]) >= oy + height + 0.5) {
        return Ok(None);
    }
    if width != 0.0 && (a[0].max(b[0]) < ox - 0.5 || a[0].min(b[0]) >= ox + width + 0.5) {
        return Ok(None);
    }
    let (dx, dy) = (b[0] - a[0], b[1] - a[1]);
    let count = dx.abs().max(dy.abs()).ceil().max(1.0) as usize;
    for i in 1..=count {
        if i % 64 == 1 {
            check(cancel)?;
        }
        let weight = i as f64 / count as f64;
        let (x, y) = (a[0] + dx * weight, a[1] + dy * weight);
        if solid(terrain, x, y) {
            return Ok(Some([x, y, a[2] + (b[2] - a[2]) * weight]));
        }
    }
    Ok(None)
}
#[derive(Clone)]
struct Trace {
    path: Vec<Point>,
    events: Vec<Value>,
    impact: Option<Point>,
}
fn trajectory(s: &Settings, power: f64, step: f64, cancel: &AtomicBool) -> Result<Trace, String> {
    check(cancel)?;
    let (parts, events) = segments(s, power, cancel)?;
    let mut path = vec![];
    let mut impact = None;
    let terrain = s.env.get("terrain").filter(|t| truth(t));
    for seg in parts {
        let duration = seg.end - seg.start;
        let count = (duration / step).ceil().max(1.0) as usize;
        for index in 0..=count {
            if index % 32 == 0 {
                check(cancel)?;
            }
            let time = seg.start + duration * index as f64 / count as f64;
            let (x, y) = seg.at(time);
            let point = [x, y, time];
            if let Some(terrain) = terrain {
                if time > 0.0 {
                    impact = if let Some(last) = path.last() {
                        swept(terrain, *last, point, cancel)?
                    } else if solid(terrain, x, y) {
                        Some(point)
                    } else {
                        None
                    };
                    if let Some(hit) = impact {
                        path.push(hit);
                        break;
                    }
                }
            }
            path.push(point);
        }
        if impact.is_some() {
            break;
        }
    }
    Ok(Trace {
        path,
        events,
        impact,
    })
}
fn closest(
    path: &[Point],
    x: f64,
    y: f64,
    cancel: &AtomicBool,
) -> Result<(f64, Option<Point>), String> {
    check(cancel)?;
    let mut best = if path.len() == 1 {
        ((path[0][0] - x).hypot(path[0][1] - y), Some(path[0]))
    } else {
        (f64::INFINITY, None)
    };
    for (index, pair) in path.windows(2).enumerate() {
        if index % 64 == 0 {
            check(cancel)?;
        }
        let (a, b) = (pair[0], pair[1]);
        let (dx, dy) = (b[0] - a[0], b[1] - a[1]);
        let length = dx * dx + dy * dy;
        let weight = if length == 0.0 {
            0.0
        } else {
            (((x - a[0]) * dx + (y - a[1]) * dy) / length).clamp(0.0, 1.0)
        };
        let (px, py) = (a[0] + weight * dx, a[1] + weight * dy);
        let distance = (px - x).hypot(py - y);
        if distance < best.0 {
            best = (distance, Some([px, py, a[2] + weight * (b[2] - a[2])]))
        }
    }
    Ok(best)
}
struct Search<'a> {
    s: &'a Settings,
    cancel: &'a AtomicBool,
    cache: Vec<(i32, (f64, Option<Point>))>,
    indices: HashMap<i32, usize>,
}
impl Search<'_> {
    fn evaluate(&mut self, power: i32) -> Result<f64, String> {
        check(self.cancel)?;
        if let Some(index) = self.indices.get(&power) {
            return Ok(self.cache[*index].1 .0);
        }
        let trace = trajectory(self.s, power as f64, 0.04, self.cancel)?;
        let best = closest(&trace.path, self.s.target_x, self.s.target_y, self.cancel)?;
        self.indices.insert(power, self.cache.len());
        self.cache.push((power, best));
        Ok(best.0)
    }
    fn best(&self) -> i32 {
        // Python's min preserves the first inserted candidate when tied.
        self.cache
            .iter()
            .min_by(|a, b| a.1 .0.total_cmp(&b.1 .0))
            .unwrap()
            .0
    }
}
fn xy(path: &[Point]) -> Vec<[f64; 2]> {
    path.iter().map(|p| [p[0], p[1]]).collect()
}
fn solve_extended(s: &Settings, cancel: &AtomicBool) -> Result<Value, String> {
    check(cancel)?;
    let minimum = s
        .env
        .get("learnedLaunch")
        .and_then(|x| x.get("power_range"))
        .and_then(Value::as_array)
        .and_then(|a| a.first())
        .and_then(Value::as_f64)
        .unwrap_or(1.0)
        .ceil()
        .max(1.0) as i32;
    let maximum = s.max_power as i32;
    if minimum > maximum {
        return Err("invalid power interval".into());
    }
    let tolerance = n(&s.env, "hitTolerance", 35.0);
    let mut search = Search {
        s,
        cancel,
        cache: vec![],
        indices: HashMap::new(),
    };
    let (tornado, mirrors) = weather(&s.env);
    let mut fast_power = None;
    let mut fine_trace = None;
    if n(&s.env, "nativeEulerStep", 0.0) == 0.0
        && tornado.is_empty()
        && mirrors.is_empty()
        && s.shot == 0
        && !s.backshot
    {
        let (x, y, side) = s.origin();
        let (dx, dy) = (s.target_x - x, s.target_y - y);
        let a = (s.angle + s.angle_offset).to_radians();
        let (c, sn) = (a.cos(), a.sin());
        let (ax, ay) = s.acceleration();
        let numerator = 2.0 * (dy * c + side * dx * sn);
        let denominator = ay * c + side * ax * sn;
        if denominator.abs() > EPS && numerator / denominator > 0.0 {
            let time = (numerator / denominator).sqrt();
            let speed =
                side * (dx / time - 0.5 * ax * time) * c - (dy / time - 0.5 * ay * time) * sn;
            let exact = (speed - s.speed_offset) / s.power_scale;
            if minimum as f64 <= exact && exact <= s.max_power && time <= s.max_time {
                let seed = exact.round_ties_even() as i32;
                let mut candidate = None;
                for power in minimum.max(seed - 2)..=maximum.min(seed + 2) {
                    let value = search.evaluate(power)?;
                    if candidate.is_none_or(|(_, best)| value < best) {
                        candidate = Some((power, value));
                    }
                }
                if let Some((power, _)) = candidate {
                    let fine = trajectory(s, power as f64, 0.02, cancel)?;
                    let verified = closest(&fine.path, s.target_x, s.target_y, cancel)?.0;
                    if verified <= tolerance.min(1.0_f64.max(tolerance * 0.15)) {
                        fast_power = Some(power);
                        fine_trace = Some(fine);
                    }
                }
            }
        }
    }
    let mut grid = vec![];
    if fast_power.is_none() {
        let step = if !tornado.is_empty() || !mirrors.is_empty() {
            1
        } else {
            8
        };
        grid.extend((minimum..=maximum).step_by(step));
        grid.push(maximum);
    }
    for power in &grid {
        search.evaluate(*power)?;
    }
    let mut minima = vec![];
    for (index, power) in grid.iter().copied().enumerate() {
        if (index == 0 || search.evaluate(power)? <= search.evaluate(grid[index - 1])?)
            && (index == grid.len() - 1
                || search.evaluate(power)? <= search.evaluate(grid[index + 1])?)
        {
            minima.push(power);
        }
    }
    for power in minima {
        for fine in minimum.max(power - 8)..=maximum.min(power + 8) {
            search.evaluate(fine)?;
        }
    }
    let power = fast_power.unwrap_or_else(|| search.best());
    let trace = match fine_trace {
        Some(trace) => trace,
        None => trajectory(s, power as f64, 0.02, cancel)?,
    };
    let (error, end) = closest(&trace.path, s.target_x, s.target_y, cancel)?;
    let Some(end) = end else {
        return Ok(json!({"reachable":false,"reason":"No hay trayectoria válida."}));
    };
    let origin = s.origin();
    let approximate = s.approximate()
        || s.shot > 0
        || s.env.get("terrain").map(truth).unwrap_or(false)
        || !trace.events.is_empty()
        || s.weather != "Normal";
    let reachable = error <= tolerance;
    let path = xy(&trace.path);
    let mut result = json!({"reachable":reachable,"reason":if reachable{""}else{"Ninguna potencia alcanza el objetivo con este ángulo."},
        "power":power,"exact_power":power as f64,"required":power,"time":rounded(end[2],3),"error":rounded(error,2),
        "path":path,"projectile_paths":[path],"display_paths":[path],"interactions":trace.events,"impacts":[trace.impact],"deployment":null,
        "cluster_hits":if error<=tolerance{1}else{0},"projectile_count":1,"distance":(s.target_x-origin.0).hypot(s.target_y-origin.1).round_ties_even() as i64,
        "quality":if approximate{"Modelo de proyectil/clima: requiere validación con el servidor"}else{"Modelo por segmentos"},
        "approximate":approximate,"end":[end[0],end[1]],"solver":if fast_power.is_some(){"analytic-verified"}else{"search"}});
    if !reachable && s.env.get("terrain").map(truth).unwrap_or(false) && trace.impact.is_some() {
        let mut free = s.clone();
        free.env.as_object_mut().unwrap().remove("terrain");
        let reference = solve_extended(&free, cancel)?;
        if reference.get("reachable").and_then(Value::as_bool) == Some(true) {
            let reference_power = reference["power"].as_f64().unwrap();
            let blocked = trajectory(s, reference_power, 0.02, cancel)?;
            let object = result.as_object_mut().unwrap();
            object.insert("blocked".into(), json!(true));
            object.insert("guide_power".into(), reference["power"].clone());
            object.insert("preview_power".into(), reference["power"].clone());
            object.insert("preview_paths".into(), json!([xy(&blocked.path)]));
            object.insert(
                "reason".into(),
                json!("El terreno bloquea la salida o el recorrido; ajusta el ángulo."),
            );
        }
    }
    check(cancel)?;
    Ok(result)
}
fn solve_base(s: &Settings, cancel: &AtomicBool) -> Result<Value, String> {
    let (x, y, side) = s.origin();
    let (dx, dy) = (s.target_x - x, s.target_y - y);
    let angle = s.angle.to_radians();
    let (ax, ay) = s.acceleration();
    let (c, sn) = (angle.cos(), angle.sin());
    let numerator = 2.0 * (dy * c + side * dx * sn);
    let denominator = ay * c + side * ax * sn;
    if denominator.abs() < 1e-9 || numerator / denominator <= 0.0 {
        return Ok(
            json!({"reachable":false,"reason":"Este ángulo y viento no alcanzan el objetivo."}),
        );
    }
    let time = (numerator / denominator).sqrt();
    let vx = dx / time - 0.5 * ax * time;
    let vy = dy / time - 0.5 * ay * time;
    let speed = side * vx * c - vy * sn;
    let exact = speed / s.power_scale;
    if exact <= 0.0 || exact > s.max_power || time > s.max_time {
        return Ok(
            json!({"reachable":false,"reason":"Se necesita otra orientación o un ángulo distinto.","required":rounded(exact,2)}),
        );
    }
    let power = exact.round_ties_even();
    let actual = s.speed(power);
    let end = [
        x + side * actual * c * time + 0.5 * ax * time * time,
        y - actual * sn * time + 0.5 * ay * time * time,
    ];
    let error = (end[0] - s.target_x).hypot(end[1] - s.target_y);
    let count = ((time / 0.02) as usize).clamp(25, 400);
    let mut path = vec![];
    for i in 0..=count {
        if i % 32 == 0 {
            check(cancel)?;
        }
        let clock = time * i as f64 / count as f64;
        path.push([
            x + side * actual * c * clock + 0.5 * ax * clock * clock,
            y - actual * sn * clock + 0.5 * ay * clock * clock,
        ]);
    }
    check(cancel)?;
    let approximate = s.approximate() || s.weather != "Normal";
    Ok(
        json!({"reachable":true,"power":power as i64,"exact_power":rounded(exact,3),"time":rounded(time,3),"error":rounded(error,2),"path":path,
        "distance":dx.hypot(dy).round_ties_even() as i64,"quality":if approximate{"Modelo base: validar disparo especial/clima"}else{"Modelo balístico base"},"approximate":approximate,"end":end}),
    )
}
pub fn solve(input: &Value, cancel: &AtomicBool) -> Result<Value, String> {
    check(cancel)?;
    let mut s = Settings::parse(input)?;
    let limits = s.env.get("learnedLaunch").filter(|x| truth(x)).cloned();
    let mut bounds = None;
    if let Some(limits) = &limits {
        let key = format!("dragonbound:{}:{}", s.mobile, s.shot);
        let valid = (|| {
            if limits.get("key").and_then(Value::as_str) != Some(key.as_str()) {
                return None;
            }
            let range = limits.get("power_range")?.as_array()?;
            if range.len() != 2 {
                return None;
            }
            let (lo, hi) = (range[0].as_f64()?, range[1].as_f64()?);
            let horizon = limits.get("max_flight_seconds")?.as_f64()?;
            if !(1.0 <= lo && lo < hi && hi <= 400.0 && 0.0 < horizon && horizon <= 20.0) {
                return None;
            }
            Some((lo, hi, horizon))
        })();
        let Some((lo, hi, horizon)) = valid else {
            return Ok(
                json!({"reachable":false,"reason":"Los límites del modelo aprendido no son válidos."}),
            );
        };
        bounds = Some((lo, hi));
        s.max_time = s.max_time.min(horizon);
        s.max_power = s.max_power.min(hi.floor());
    }
    let extended = s.env.as_object().is_some_and(|x| !x.is_empty())
        || s.shot > 0
        || s.quantize
        || s.speed_offset != 0.0
        || s.angle_offset != 0.0
        || s.backshot;
    let mut result = if extended {
        solve_extended(&s, cancel)?
    } else {
        solve_base(&s, cancel)?
    };
    if let (Some(limits), Some((lo, hi))) = (limits, bounds) {
        for key in ["power", "guide_power", "preview_power"] {
            if let Some(power) = result.get(key).and_then(Value::as_f64) {
                if power < lo || power > hi {
                    return Ok(
                        json!({"reachable":false,"reason":"Este ángulo queda fuera de la fuerza comprobada; cambia el ángulo.","learned_launch":limits}),
                    );
                }
            }
        }
        result
            .as_object_mut()
            .unwrap()
            .insert("learned_launch".into(), limits);
    }
    Ok(result)
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn half_even_and_negative_floor_are_preserved() {
        assert_eq!(2.5_f64.round_ties_even(), 2.0);
        assert_eq!((-2.5_f64).round_ties_even(), -2.0);
        let s =
            Settings::parse(&json!({"wind":1,"wind_angle":180,"wind_scale":1,"wind_mode":"floor"}))
                .unwrap();
        assert_eq!(s.acceleration().0, -1.0);
        assert_eq!(rounded(2.675, 2), 2.67);
        assert_eq!(weather_kind(&json!({"typeId":7.0})), Some(7));
        assert_eq!(weather_kind(&json!({"name":"mIrRoR"})), None);
    }
    #[test]
    fn cancellation_and_unsupported_do_not_produce_a_fake_solution() {
        let cancelled = AtomicBool::new(true);
        assert_eq!(solve(&json!({}), &cancelled).unwrap_err(), "cancelled");
        assert!(solve(&json!({"mobile":"NAK"}), &AtomicBool::new(false))
            .unwrap_err()
            .starts_with("unsupported:"));
        assert!(solve(
            &json!({"environment":{"activeWeathers":[{"typeId":7}]}}),
            &AtomicBool::new(false)
        )
        .unwrap_err()
        .starts_with("unsupported:"));
        assert!(solve(
            &json!({"environment":{"terrain":{"polygon":[[1,2,3]]}}}),
            &AtomicBool::new(false)
        )
        .unwrap_err()
        .starts_with("unsupported:"));
    }
    #[test]
    fn controlled_normal_high_and_blocked_searches_match_power() {
        let mut input = json!({"angle":60,"hero_x":150,"hero_y":400,"target_x":700,"target_y":400,"gravity":396,"power_scale":2.45,"muzzle":false,"environment":{"terrain":{"polygon":[[0,450],[1200,450],[1200,900],[0,900]]},"hitTolerance":18}});
        let cancel = AtomicBool::new(false);
        let normal = solve(&input, &cancel).unwrap();
        assert_eq!(normal["power"], 205);
        assert_eq!(normal["reachable"], true);
        input["angle"] = json!(82);
        let high = solve(&input, &cancel).unwrap();
        assert_eq!(high["power"], 363);
        input["angle"] = json!(60);
        input["environment"]["terrain"] =
            json!({"polygon":[[100,370],[200,370],[200,430],[100,430]]});
        let blocked = solve(&input, &cancel).unwrap();
        assert_eq!(blocked["blocked"], true);
        assert_eq!(blocked["guide_power"], 205.0);
    }
    #[test]
    fn single_pixel_and_sorted_rle_terrain_use_the_same_coordinate_rounding() {
        assert!(solid(&json!({"heights":[null,null,4]}), 2.5, 4.0));
        assert!(solid(
            &json!({"width":6,"height":1,"rows":[[2,4]],"rowsSorted":true}),
            2.0,
            0.0
        ));
        assert!(!solid(
            &json!({"width":6,"height":1,"rows":[[2,4]],"rowsSorted":true}),
            4.0,
            0.0
        ));
    }
    #[test]
    fn cancellation_interrupts_an_in_flight_weather_search() {
        use std::sync::{mpsc, Arc};
        use std::time::Duration;
        let cancel = Arc::new(AtomicBool::new(false));
        let worker_cancel = cancel.clone();
        let (started, ready) = mpsc::channel();
        let worker = std::thread::spawn(move || {
            let input = json!({"angle":82,"hero_x":0,"hero_y":0,"target_x":120000,"target_y":1000,
                "gravity":396,"power_scale":2.45,"muzzle":false,"max_power":2000,"max_time":60,
                "environment":{"mapHeight":20000000,"activeWeathers":[{"typeId":7,"x":400},{"typeId":7,"x":800},{"typeId":8,"x":2000,"size":160}],"hitTolerance":18}});
            started.send(()).unwrap();
            solve(&input, &worker_cancel)
        });
        ready.recv_timeout(Duration::from_secs(2)).unwrap();
        std::thread::sleep(Duration::from_millis(1));
        cancel.store(true, Ordering::Relaxed);
        assert_eq!(worker.join().unwrap().unwrap_err(), "cancelled");
    }
    #[test]
    fn learned_limits_are_closed_and_never_borrow_another_weapon() {
        let input = json!({"angle":60,"hero_x":150,"hero_y":400,"target_x":700,"target_y":400,
            "gravity":396,"power_scale":2.45,"muzzle":false,"environment":{"hitTolerance":18,
                "learnedLaunch":{"key":"dragonbound:ARMOR:0","power_range":[100,250],"max_flight_seconds":4}}});
        let cancel = AtomicBool::new(false);
        let result = solve(&input, &cancel).unwrap();
        assert_eq!(result["power"], 205);
        assert_eq!(result["reachable"], true);
        assert!(result.get("learned_launch").is_some());
        let mut invalid = input;
        invalid["environment"]["learnedLaunch"]["key"] = json!("dragonbound:ICE:0");
        let rejected = solve(&invalid, &cancel).unwrap();
        assert_eq!(rejected["reachable"], false);
        assert!(rejected.get("power").is_none());
    }
}
