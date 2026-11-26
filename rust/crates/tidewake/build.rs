//! On Windows, embed the Common Controls v6 manifest and the app icon.

fn main() {
    #[cfg(target_os = "windows")]
    {
        let mut res = winres::WindowsResource::new();
        res.set_manifest_file("windows/tidewake.exe.manifest");
        res.set_icon("windows/tidewake.ico");
        res.compile().expect("embed Windows manifest and icon");
    }
}
