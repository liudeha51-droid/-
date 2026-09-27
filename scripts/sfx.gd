class_name Sfx
extends Node
## Placeholder sound effects synthesised at startup, so the prototype has
## audio feedback without shipping any files. Swap for recorded/produced
## sounds by assigning streams in `sounds` (see docs/GAME_DESIGN.md, Audio).

static var instance: Sfx

const RATE := 22050
var sounds := {}
var _players: Array[AudioStreamPlayer] = []
var _next := 0
var _rng := RandomNumberGenerator.new()


func _ready() -> void:
	instance = self
	for i in 16:
		var p := AudioStreamPlayer.new()
		p.volume_db = -8.0
		add_child(p)
		_players.append(p)
	sounds["swing"] = _synth(0.18, func(t, u): return _noise() * _env(u, 0.05) * (0.3 + 0.7 * u))
	sounds["boss_swing"] = _synth(0.35, func(t, u): return _noise() * _env(u, 0.2) * 0.9)
	sounds["hit"] = _synth(0.2, func(t, u): return (sin(TAU * lerpf(160.0, 60.0, u) * t) * 0.8 + _noise() * 0.4 * (1.0 - u)) * _env(u, 0.01))
	sounds["hurt"] = _synth(0.3, func(t, u): return _square(lerpf(420.0, 110.0, u) * t) * 0.5 * _env(u, 0.01))
	sounds["graze"] = _synth(0.05, func(t, u): return sin(TAU * 2400.0 * t) * 0.35 * (1.0 - u))
	sounds["shoot"] = _synth(0.08, func(t, u): return _square(lerpf(900.0, 600.0, u) * t) * 0.18 * (1.0 - u))
	sounds["enemy_shot"] = _synth(0.1, func(t, u): return sin(TAU * lerpf(1300.0, 700.0, u) * t) * 0.25 * (1.0 - u))
	sounds["dodge"] = _synth(0.25, func(t, u): return _noise() * 0.35 * sin(PI * u))
	sounds["heal"] = _synth(0.7, func(t, u): return (sin(TAU * 523.0 * t) + sin(TAU * 784.0 * t) * (1.0 if u > 0.3 else 0.0)) * 0.25 * _env(u, 0.05))
	sounds["shatter"] = _synth(0.25, func(t, u): return (_noise() * 0.5 + sin(TAU * 3100.0 * t) * 0.3) * pow(1.0 - u, 3.0))
	sounds["spell"] = _synth(1.2, func(t, u): return (sin(TAU * 440.0 * t) + sin(TAU * 554.0 * t) + sin(TAU * 659.0 * t) + sin(TAU * 880.0 * t * (1.0 + u * 0.02))) * 0.14 * _env(u, 0.02))
	sounds["rest"] = _synth(1.5, func(t, u): return (sin(TAU * 392.0 * t) + sin(TAU * 587.0 * t)) * 0.22 * _env(u, 0.1))
	sounds["death"] = _synth(1.6, func(t, u): return (_square(lerpf(220.0, 55.0, u) * t) * 0.3 + _noise() * 0.1) * (1.0 - u))
	sounds["victory"] = _synth(1.8, func(t, u): return sin(TAU * [523.0, 659.0, 784.0, 1046.0][mini(int(u * 4.0), 3)] * t) * 0.3 * _env(u, 0.02))


static func play(sound: String, pitch_jitter := 0.08, volume_db := -8.0) -> void:
	if instance == null or not instance.sounds.has(sound):
		return
	var p: AudioStreamPlayer = instance._players[instance._next]
	instance._next = (instance._next + 1) % instance._players.size()
	p.stream = instance.sounds[sound]
	p.pitch_scale = 1.0 + instance._rng.randf_range(-pitch_jitter, pitch_jitter)
	p.volume_db = volume_db
	p.play()


func _synth(duration: float, fn: Callable) -> AudioStreamWAV:
	var n := int(RATE * duration)
	var data := PackedByteArray()
	data.resize(n * 2)
	for i in n:
		var t := float(i) / RATE
		var s: float = fn.call(t, float(i) / n)
		data.encode_s16(i * 2, int(clampf(s, -1.0, 1.0) * 32000.0))
	var w := AudioStreamWAV.new()
	w.format = AudioStreamWAV.FORMAT_16_BITS
	w.mix_rate = RATE
	w.stereo = false
	w.data = data
	return w


func _noise() -> float:
	return _rng.randf_range(-1.0, 1.0)


static func _square(phase: float) -> float:
	return 1.0 if fmod(phase, 1.0) < 0.5 else -1.0


## Attack/decay envelope: quick attack over `a` (0..1 of duration), then linear decay.
static func _env(u: float, a: float) -> float:
	return u / a if u < a else 1.0 - (u - a) / (1.0 - a)
