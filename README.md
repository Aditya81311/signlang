# signlang

A two-way sign language translator for ASL fingerspelling, written in Python.

- **Sign to speech:** hold a hand sign up to your webcam. The program picks out the letter, builds a word, and reads it aloud.
- **Speech to sign:** say a phrase into your microphone. The program shows the matching letter images one by one.

This is a demo built with classical computer vision (OpenCV). It does not use a trained model. See [Limitations](#limitations) before you try it.

## How it works

### Sign to speech

1. Each webcam frame is converted to grayscale, blurred, and thresholded (Otsu) to separate the hand from the background.
2. The largest contour in the frame is treated as the hand. Contours smaller than 1000 px² are ignored.
3. Three features are measured from that contour: its area, the aspect ratio of its bounding box, and the number of convexity defects (the gaps between fingers).
4. A set of hand-written rules maps those features to a letter.
5. A letter is added to the current word only after it stays the same for more than 10 frames in a row. This stops flicker.
6. Press `s` to speak the word with pyttsx3 (offline text-to-speech).

### Speech to sign

1. The microphone records one phrase.
2. Google's speech recognition (via the SpeechRecognition library) turns it into text.
3. For each letter, the program opens `signs/<letter>.jpg` and shows it for 1 second. Spaces use `signs/space.jpg`. Missing images are skipped with a message.

## Project structure

```
signlang/
├── signs/             # one image per letter (a.jpg, b.jpg, ... z.jpg) plus space.jpg
├── model.py           # command-line app with both modes
├── webmodel.py        # Flask version
├── requirements.txt
└── README.md
```

## Setup

You need Python 3.13, a webcam, and a microphone. Python 3.13 is what the pinned `audioop-lts`, `standard-aifc` and `standard-chunk` packages are for.

```bash
git clone https://github.com/Aditya81311/signlang.git
cd signlang

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

PyAudio can fail to install on some systems:

- Ubuntu/Debian: `sudo apt install portaudio19-dev`, then run `pip install` again
- macOS: `brew install portaudio`
- Windows: install a prebuilt PyAudio wheel

## Usage

```bash
python model.py
```

You get a menu:

```
1. Sign to Speech Mode
2. Speech to Sign Mode
3. Exit
```

**Sign to Speech:** keep your hand in front of a plain background with good light. Hold a sign steady to add the letter.

| Key | Action |
| --- | --- |
| `s` | Speak the current word and clear it |
| `q` | Back to the menu |

**Speech to Sign:** speak when you see `Speak something...`. It listens once, then shows the signs. This mode needs an internet connection because the speech recognition runs on Google's service.

### Web version

`webmodel.py` is a Flask version of the same app. It has buttons to start and stop each mode and streams the webcam to the browser.

```bash
python webmodel.py
```

Open `http://127.0.0.1:5000`. The home page loads `templates/index.html`, which is not in the repo yet, so the web version will not load until that file is added.

## Limitations

- **Only a few letters work.** The rules can output `A`, `B`, `C`, `D`, `L`, `V`, `W`, `Y` and `space`. The other letters, and `delete`, are listed in the code but never recognised.
- **It is rule-based, not machine learning.** The rules use rough shape measurements, so different signs with similar outlines get confused. `C` is the fallback when nothing else matches.
- **It needs clean conditions.** A plain background and steady lighting matter, because the hand is found by thresholding. Anything else large in frame (a face, a bright wall) can be picked up instead.
- **Static letters only.** Signs that involve movement, like `J` and `Z`, are not handled.
- **Speech to sign handles one phrase per run** and needs internet.

## Roadmap

- [ ] Add `templates/index.html` so the web version runs
- [ ] Replace the hand-written rules with a trained classifier on hand landmarks or labelled images
- [ ] Cover all 26 letters
- [ ] Handle `J` and `Z` (motion)
- [ ] Remove unused dependencies from `requirements.txt`

## Author

**Aditya Gangurde**
[GitHub](https://github.com/Aditya81311) · [LinkedIn](https://linkedin.com/in/aditya-gangurde-9a0346320) · aditya81311@gmail.com
