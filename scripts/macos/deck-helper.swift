import CoreAudio
import Foundation

let inputs = [("RØDE PodMic USB", "PodMic"), ("MacBook Pro Microphone", "MacBook"), ("Insta360 Link 2", "Insta360")]
let outputs = [("Shade", "Shade"), ("BenQ PD3205U", "BenQ"), ("MacBook Pro Speakers", "MacBook")]
let system = AudioObjectID(kAudioObjectSystemObject)

enum Direction: String {
    case input, output

    var defaultSelector: AudioObjectPropertySelector {
        self == .input ? kAudioHardwarePropertyDefaultInputDevice : kAudioHardwarePropertyDefaultOutputDevice
    }
    var scope: AudioObjectPropertyScope {
        self == .input ? kAudioObjectPropertyScopeInput : kAudioObjectPropertyScopeOutput
    }
    var choices: [(String, String)] { self == .input ? inputs : outputs }
}

func address(_ selector: AudioObjectPropertySelector, _ scope: AudioObjectPropertyScope = kAudioObjectPropertyScopeGlobal)
    -> AudioObjectPropertyAddress
{
    AudioObjectPropertyAddress(mSelector: selector, mScope: scope, mElement: kAudioObjectPropertyElementMain)
}

func devices() -> [AudioObjectID] {
    var addr = address(kAudioHardwarePropertyDevices)
    var size: UInt32 = 0
    AudioObjectGetPropertyDataSize(system, &addr, 0, nil, &size)
    var ids = [AudioObjectID](repeating: 0, count: Int(size) / MemoryLayout<AudioObjectID>.size)
    AudioObjectGetPropertyData(system, &addr, 0, nil, &size, &ids)
    return ids
}

func name(of device: AudioObjectID) -> String {
    var addr = address(kAudioObjectPropertyName)
    var value: Unmanaged<CFString>?
    var size = UInt32(MemoryLayout<Unmanaged<CFString>?>.size)
    guard AudioObjectGetPropertyData(device, &addr, 0, nil, &size, &value) == noErr, let value else { return "" }
    return value.takeRetainedValue() as String
}

func isBluetooth(_ device: AudioObjectID) -> Bool {
    var addr = address(kAudioDevicePropertyTransportType)
    var transport: UInt32 = 0
    var size = UInt32(MemoryLayout<UInt32>.size)
    AudioObjectGetPropertyData(device, &addr, 0, nil, &size, &transport)
    return transport == kAudioDeviceTransportTypeBluetooth || transport == kAudioDeviceTransportTypeBluetoothLE
}

func hasStreams(_ device: AudioObjectID, _ direction: Direction) -> Bool {
    var addr = address(kAudioDevicePropertyStreams, direction.scope)
    var size: UInt32 = 0
    AudioObjectGetPropertyDataSize(device, &addr, 0, nil, &size)
    return size > 0
}

func find(_ deviceName: String, _ direction: Direction) -> AudioObjectID? {
    devices().first { name(of: $0) == deviceName && hasStreams($0, direction) }
}

func current(_ direction: Direction) -> AudioObjectID {
    var addr = address(direction.defaultSelector)
    var device: AudioObjectID = 0
    var size = UInt32(MemoryLayout<AudioObjectID>.size)
    AudioObjectGetPropertyData(system, &addr, 0, nil, &size, &device)
    return device
}

func select(_ device: AudioObjectID, _ direction: Direction) {
    var addr = address(direction.defaultSelector)
    var value = device
    AudioObjectSetPropertyData(system, &addr, 0, nil, UInt32(MemoryLayout<AudioObjectID>.size), &value)
}

func label(_ direction: Direction) -> String {
    let deviceName = name(of: current(direction))
    return direction.choices.first { $0.0 == deviceName }?.1 ?? deviceName
}

func cycle(_ direction: Direction) {
    let present = direction.choices.compactMap { find($0.0, direction) }
    guard !present.isEmpty else { return }
    let index = present.firstIndex(of: current(direction)).map { $0 + 1 } ?? 0
    select(present[index % present.count], direction)
}

func onChange(_ selector: AudioObjectPropertySelector, _ handler: @escaping () -> Void) {
    var addr = address(selector)
    AudioObjectAddPropertyListenerBlock(system, &addr, .main) { _, _ in handler() }
}

// A reconnecting Bluetooth headset claims the default input, and opening its mic drops playback to the
// hands-free profile. Only react to device arrivals so a deliberate pick of the headset mic sticks.
func guardInput() {
    let enforce = {
        guard isBluetooth(current(.input)),
            let preferred = inputs.lazy.compactMap({ find($0.0, .input) }).first
        else { return }
        select(preferred, .input)
    }
    enforce()
    onChange(kAudioHardwarePropertyDevices) {
        DispatchQueue.main.asyncAfter(deadline: .now() + 1, execute: enforce)
    }
    dispatchMain()
}

final class Plugin {
    let socket: URLSessionWebSocketTask
    var contexts: [String: String] = [:]
    var weather = ("…", "", "")

    init(port: String, uuid: String, registerEvent: String) {
        socket = URLSession.shared.webSocketTask(with: URL(string: "ws://127.0.0.1:\(port)")!)
        socket.resume()
        send(["event": registerEvent, "uuid": uuid])
        receive()
        for selector in [
            kAudioHardwarePropertyDefaultInputDevice, kAudioHardwarePropertyDefaultOutputDevice,
            kAudioHardwarePropertyDevices,
        ] {
            onChange(selector) { [weak self] in self?.renderAll() }
        }
        Timer.scheduledTimer(withTimeInterval: 900, repeats: true) { [weak self] _ in self?.fetchWeather() }
        fetchWeather()
    }

    func send(_ message: [String: Any]) {
        guard let data = try? JSONSerialization.data(withJSONObject: message) else { return }
        socket.send(.string(String(decoding: data, as: UTF8.self))) { _ in }
    }

    func receive() {
        socket.receive { [weak self] result in
            switch result {
            case .success(.string(let text)):
                DispatchQueue.main.async { self?.handle(text) }
                self?.receive()
            case .success:
                self?.receive()
            case .failure:
                exit(0)
            }
        }
    }

    func handle(_ text: String) {
        guard let event = try? JSONSerialization.jsonObject(with: Data(text.utf8)) as? [String: Any],
            let context = event["context"] as? String, let action = event["action"] as? String
        else { return }
        switch event["event"] as? String {
        case "willAppear":
            contexts[context] = action
            render(context)
        case "willDisappear":
            contexts[context] = nil
        case "keyDown":
            switch action.split(separator: ".").last {
            case "input": cycle(.input)
            case "output": cycle(.output)
            default: fetchWeather()
            }
            renderAll()
        default:
            break
        }
    }

    func renderAll() { contexts.keys.forEach(render) }

    func render(_ context: String) {
        switch contexts[context]?.split(separator: ".").last {
        case "input": send(["event": "setTitle", "context": context, "payload": ["title": label(.input)]])
        case "output": send(["event": "setTitle", "context": context, "payload": ["title": label(.output)]])
        case "weather": send(["event": "setImage", "context": context, "payload": ["image": weatherImage()]])
        default: break
        }
    }

    func weatherImage() -> String {
        let (temperature, humidity, wind) = weather
        let line = { (y: Int, size: Int, color: String, text: String) in
            "<text x=\"72\" y=\"\(y)\" font-size=\"\(size)\" fill=\"\(color)\" text-anchor=\"middle\" "
                + "font-family=\"Helvetica\" font-weight=\"bold\">\(text)</text>"
        }
        let svg =
            "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"144\" height=\"144\"><rect width=\"144\" height=\"144\" fill=\"black\"/>"
            + line(52, 40, "#f0883e", temperature) + line(92, 26, "#39c5cf", humidity) + line(128, 26, "#c9d1d9", wind)
            + "</svg>"
        return "data:image/svg+xml;base64," + Data(svg.utf8).base64EncodedString()
    }

    func fetchWeather() {
        let url = URL(string: "https://wttr.in/34.17,-118.61?m&format=%25t%7C%25h%7C%25w")!
        URLSession.shared.dataTask(with: url) { [weak self] data, response, _ in
            guard (response as? HTTPURLResponse)?.statusCode == 200, let data else { return }
            let fields = String(decoding: data, as: UTF8.self).trimmingCharacters(in: .whitespacesAndNewlines)
                .split(separator: "|").map(String.init)
            guard fields.count == 3 else { return }
            DispatchQueue.main.async {
                self?.weather = (fields[0].replacingOccurrences(of: "+", with: ""), fields[1], fields[2])
                self?.renderAll()
            }
        }.resume()
    }
}

let arguments = Array(CommandLine.arguments.dropFirst())
switch arguments.first {
case "guard":
    guardInput()
case "cycle", "current":
    guard arguments.count == 2, let direction = Direction(rawValue: arguments[1]) else {
        FileHandle.standardError.write(Data("usage: deck-helper cycle|current input|output\n".utf8))
        exit(2)
    }
    if arguments[0] == "cycle" { cycle(direction) }
    print(label(direction))
default:
    let options = Dictionary(
        stride(from: 0, to: arguments.count - 1, by: 2).map { (arguments[$0], arguments[$0 + 1]) },
        uniquingKeysWith: { $1 })
    guard let port = options["-port"], let uuid = options["-pluginUUID"], let event = options["-registerEvent"] else {
        FileHandle.standardError.write(Data("usage: deck-helper guard | cycle|current input|output\n".utf8))
        exit(2)
    }
    let plugin = Plugin(port: port, uuid: uuid, registerEvent: event)
    withExtendedLifetime(plugin) { dispatchMain() }
}
