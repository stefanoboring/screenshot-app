// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "ScreenshotApp",
    platforms: [.iOS(.v16), .macOS(.v13)],
    products: [.library(name: "ScreenshotApp", targets: ["ScreenshotApp"]), .executable(name: "ScreenshotAppApp", targets: ["ScreenshotAppApp"])],
    targets: [
        .target(name: "ScreenshotApp", path: "ScreenshotApp", exclude: ["ScreenshotApp.swift"]),
        .executableTarget(name: "ScreenshotAppApp", dependencies: ["ScreenshotApp"], path: "ScreenshotAppApp"),
        .testTarget(name: "ScreenshotAppTests", dependencies: ["ScreenshotApp"], path: "ScreenshotAppTests")
    ]
)
