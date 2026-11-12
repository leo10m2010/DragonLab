//! Versioned C boundary. Every allocation is released by the same Rust library.
mod engine;
use std::ffi::{c_char, CString};
use std::panic::{catch_unwind, AssertUnwindSafe};
use std::sync::atomic::{AtomicBool, Ordering};

#[no_mangle]
pub extern "C" fn dl_core_version() -> u32 {
    1
}

#[no_mangle]
pub extern "C" fn dl_cancel_new() -> *mut AtomicBool {
    Box::into_raw(Box::new(AtomicBool::new(false)))
}

/// # Safety
/// `handle` must be null or a live handle returned by dl_cancel_new.
#[no_mangle]
pub unsafe extern "C" fn dl_cancel_set(handle: *mut AtomicBool) {
    if let Some(flag) = handle.as_ref() {
        flag.store(true, Ordering::Relaxed);
    }
}

/// # Safety
/// Caller must unregister cancellation callbacks and finish solving first.
/// The handle must be null or an unfreed return from dl_cancel_new.
#[no_mangle]
pub unsafe extern "C" fn dl_cancel_free(handle: *mut AtomicBool) {
    if !handle.is_null() {
        drop(Box::from_raw(handle));
    }
}

/// # Safety
/// Input must reference `len` readable bytes. Handle must remain live until return.
/// Returns owned UTF-8 JSON; release it exactly once with dl_string_free.
#[no_mangle]
pub unsafe extern "C" fn dl_solve_json(
    input: *const u8,
    len: usize,
    handle: *const AtomicBool,
) -> *mut c_char {
    let output = catch_unwind(AssertUnwindSafe(|| {
        if input.is_null() || len == 0 || len > 16 * 1024 * 1024 {
            return serde_json::json!({"error":"invalid request size"});
        }
        let request = match serde_json::from_slice::<serde_json::Value>(std::slice::from_raw_parts(
            input, len,
        )) {
            Ok(value) => value,
            Err(_) => return serde_json::json!({"error":"invalid request JSON"}),
        };
        let local = AtomicBool::new(false);
        let cancel = handle.as_ref().unwrap_or(&local);
        match engine::solve(&request, cancel) {
            Ok(result) => serde_json::json!({"result":result}),
            Err(error) => serde_json::json!({"error":error}),
        }
    }))
    .unwrap_or_else(|_| serde_json::json!({"error":"native computation failed"}));
    // JSON serialization escapes NUL bytes, so CString construction cannot fail.
    CString::new(output.to_string()).unwrap().into_raw()
}

/// # Safety
/// Pointer must be null or an unmodified, unfreed return from dl_solve_json.
#[no_mangle]
pub unsafe extern "C" fn dl_string_free(value: *mut c_char) {
    if !value.is_null() {
        drop(CString::from_raw(value));
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::ffi::CStr;
    #[test]
    fn rejects_invalid_json_and_frees_response() {
        unsafe {
            let result = dl_solve_json(b"{".as_ptr(), 1, std::ptr::null());
            assert!(CStr::from_ptr(result)
                .to_str()
                .unwrap()
                .contains("invalid request JSON"));
            dl_string_free(result);
        }
    }
    #[test]
    fn cancellation_handle_has_explicit_ownership() {
        unsafe {
            let handle = dl_cancel_new();
            assert!(!(*handle).load(Ordering::Relaxed));
            dl_cancel_set(handle);
            assert!((*handle).load(Ordering::Relaxed));
            dl_cancel_free(handle);
        }
    }
}
