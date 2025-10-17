"""
Analyze MIDI file structure to understand the drum notes
"""
import pretty_midi

midi_path = r"D:\Coding Files\GitHub\drumscore-be\test_output\baseline_omnizart.mid"

# Load MIDI file
midi_data = pretty_midi.PrettyMIDI(midi_path)

print("=" * 70)
print("MIDI File Analysis")
print("=" * 70)

print(f"\nFile: {midi_path}")
print(f"Tempo: {midi_data.get_tempo_changes()}")
print(f"Duration: {midi_data.get_end_time():.2f} seconds")
print(f"Number of instruments: {len(midi_data.instruments)}")

for i, instrument in enumerate(midi_data.instruments):
    print(f"\n--- Instrument {i} ---")
    print(f"Name: {instrument.name}")
    print(f"Program: {instrument.program}")
    print(f"Is drum: {instrument.is_drum}")
    print(f"Number of notes: {len(instrument.notes)}")
    
    # Collect unique MIDI pitches
    pitches = {}
    for note in instrument.notes:
        if note.pitch not in pitches:
            pitches[note.pitch] = 0
        pitches[note.pitch] += 1
    
    print(f"\nUnique MIDI pitches found:")
    for pitch, count in sorted(pitches.items()):
        note_name = pretty_midi.note_number_to_name(pitch)
        print(f"  MIDI {pitch:3d} ({note_name:5s}): {count:4d} notes")
    
    # Show first 10 notes as examples
    print(f"\nFirst 10 notes:")
    for j, note in enumerate(instrument.notes[:10]):
        note_name = pretty_midi.note_number_to_name(note.pitch)
        print(f"  {j+1}. Time: {note.start:6.2f}s | Pitch: {note.pitch:3d} ({note_name:5s}) | "
              f"Velocity: {note.velocity:3d} | Duration: {note.end - note.start:.3f}s")

print("\n" + "=" * 70)
