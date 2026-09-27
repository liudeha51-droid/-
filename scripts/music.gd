class_name Music
extends Node
## Placeholder music, synthesised at startup (the music direction is undecided).
## Two loops: a slow minor ambient piece for exploration and a driving loop for
## boss fights. Replace a track by assigning any AudioStream to `tracks[name]`.

static var instance: Music

const RATE := 16000
const FADE := 1.5

var tracks := {}
var current := ""
var _a: AudioStreamPlayer
var _b: AudioStreamPlayer
var _rng := RandomNumberGenerator.new()


func _ready() -> void:
	instance = self
	_rng.seed = 7
	_a = _player()
	_b = _player()
	tracks["explore"] = _explore_loop()
	tracks["boss"] = _boss_loop()


static func play(track: String) -> void:
	if instance:
		instance._crossfade(track)


func _crossfade(track: String) -> void:
	if track == current:
		return
	current = track
	var old := _a if _a.playing else _b
	var next := _b if old == _a else _a
	if old.playing:
		var out := create_tween()
		out.tween_property(old, "volume_db", -60.0, FADE)
		out.tween_callback(old.stop)
	if tracks.has(track):
		next.stream = tracks[track]
		next.volume_db = -60.0
		next.play()
		create_tween().tween_property(next, "volume_db", -14.0, FADE)


func _player() -> AudioStreamPlayer:
	var p := AudioStreamPlayer.new()
	p.volume_db = -60.0
	add_child(p)
	return p


# D minor. MIDI note -> Hz.
static func _hz(midi: float) -> float:
	return 440.0 * pow(2.0, (midi - 69.0) / 12.0)


## Slow, sparse and cold: a low drone with plucked notes and a long echo.
func _explore_loop() -> AudioStreamWAV:
	var seconds := 19.2  # 12 bars of 4/4 at 150 bpm halves, i.e. 8 slow pulses
	var n := int(RATE * seconds)
	var buf := PackedFloat32Array()
	buf.resize(n)
	var d2 := _hz(38)
	var a2 := _hz(45)
	for i in n:
		var t := float(i) / RATE
		var swell := 0.6 + 0.4 * sin(TAU * t / seconds)
		buf[i] = (sin(TAU * d2 * t) * 0.18 + sin(TAU * a2 * t) * 0.08 + sin(TAU * d2 * 2.0 * t + sin(t * 0.7)) * 0.04) * swell
	# Plucks: a D minor melody fragment on a 1.2 s grid, some rests.
	var melody := [74, -1, 77, 76, -1, 72, 74, -1, 69, -1, 70, 69, 67, -1, 65, -1]
	for step in melody.size():
		var note: int = melody[step]
		if note < 0:
			continue
		_pluck(buf, step * 1.2, _hz(note), 0.22, 2.4)
		if step % 4 == 0:
			_pluck(buf, step * 1.2, _hz(note - 12), 0.12, 3.0)
	_echo(buf, 0.6, 0.38)
	return _to_wav(buf, true)


## Driving boss loop: pulse bass, arpeggio and a thump on each beat.
func _boss_loop() -> AudioStreamWAV:
	var bpm := 150.0
	var beat := 60.0 / bpm
	var bars := 8
	var n := int(RATE * beat * 4 * bars)
	var buf := PackedFloat32Array()
	buf.resize(n)
	# i - VI - VII - V in D minor, two bars each.
	var roots := [38, 34, 36, 33]
	var chords := [[62, 65, 69], [58, 62, 65], [60, 64, 67], [57, 61, 64]]
	var eighth := beat * 0.5
	var sixteenth := beat * 0.25
	for bar in bars:
		var c := bar / 2
		var root: int = roots[c]
		var chord: Array = chords[c]
		for e in 8:
			var start := (bar * 4 * beat) + e * eighth
			_tone(buf, start, eighth * 0.9, _hz(root + (12 if e % 2 == 1 else 0)), 0.2, true)
		for s in 16:
			var start := (bar * 4 * beat) + s * sixteenth
			var note: int = chord[[0, 1, 2, 1][s % 4]] + (12 if s >= 8 else 0)
			_tone(buf, start, sixteenth * 0.8, _hz(note), 0.07, false)
		for b in 4:
			_thump(buf, bar * 4 * beat + b * beat)
	_echo(buf, beat * 0.75, 0.2)
	return _to_wav(buf, true)


func _pluck(buf: PackedFloat32Array, at: float, freq: float, amp: float, decay: float) -> void:
	var start := int(at * RATE)
	var length := int(decay * RATE)
	for i in length:
		var idx := start + i
		if idx >= buf.size():
			break
		var t := float(i) / RATE
		var env := exp(-t * 3.0 / decay * 2.0) * minf(1.0, t * 200.0)
		buf[idx] += (sin(TAU * freq * t) + 0.3 * sin(TAU * freq * 2.0 * t) + 0.1 * sin(TAU * freq * 3.0 * t)) * amp * env


func _tone(buf: PackedFloat32Array, at: float, dur: float, freq: float, amp: float, bass: bool) -> void:
	var start := int(at * RATE)
	var length := int(dur * RATE)
	for i in length:
		var idx := start + i
		if idx >= buf.size():
			break
		var t := float(i) / RATE
		var env := minf(1.0, t * 300.0) * (1.0 - float(i) / length)
		var ph := fmod(freq * t, 1.0)
		var w := (sin(TAU * freq * t) * 0.7 + (0.3 if ph < 0.5 else -0.3)) if bass else (1.0 - 4.0 * absf(ph - 0.5))
		buf[idx] += w * amp * env


func _thump(buf: PackedFloat32Array, at: float) -> void:
	var start := int(at * RATE)
	var length := int(0.18 * RATE)
	for i in length:
		var idx := start + i
		if idx >= buf.size():
			break
		var t := float(i) / RATE
		buf[idx] += sin(TAU * lerpf(110.0, 40.0, t / 0.18) * t) * 0.35 * (1.0 - t / 0.18)


## Wrap-around feedback echo, so the loop point stays seamless.
func _echo(buf: PackedFloat32Array, delay: float, feedback: float) -> void:
	var d := int(delay * RATE)
	var n := buf.size()
	for pass_i in 2:
		for i in n:
			buf[i] += buf[(i - d + n) % n] * feedback * (0.5 if pass_i == 1 else 1.0)


func _to_wav(buf: PackedFloat32Array, loop: bool) -> AudioStreamWAV:
	var peak := 0.001
	for v in buf:
		peak = maxf(peak, absf(v))
	var gain := 0.9 / peak
	var data := PackedByteArray()
	data.resize(buf.size() * 2)
	for i in buf.size():
		data.encode_s16(i * 2, int(clampf(buf[i] * gain, -1.0, 1.0) * 32000.0))
	var w := AudioStreamWAV.new()
	w.format = AudioStreamWAV.FORMAT_16_BITS
	w.mix_rate = RATE
	w.stereo = false
	w.data = data
	if loop:
		w.loop_mode = AudioStreamWAV.LOOP_FORWARD
		w.loop_begin = 0
		w.loop_end = buf.size()
	return w
