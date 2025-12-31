# digicam-datestamp

By using Python utility that batch-applies date/time stamps to photos using EXIF metadata, your pictures can have their datestamp on them!

I created this project initially to allow my old Nikon Coolpix pictures to have a timestamp style for photos that were originally captured without an on-image date stamp.
I knew that older digital cameras store capture time in EXIF metadata, but not always as visible text on the image, if you don't have it set up on the settings ( me :( )

### How it works:

- reads the original capture time from EXIF (`DateTimeOriginal`)
- formats it similar to Nikon's custom datestamp
- permanently renders it onto the image
- processes entire folders safely without overwriting originals.

> Tested on ~200 JPG images in under 30 seconds.

## Features

- Batch processes folders of images
- Uses EXIF `DateTimeOriginal` with safe fallback
- Automatically handles camera orientation metadata
- Never overwrites original files
- Cross-platform (Windows, macOS, Linux)
- Minimal interface: input folder → output folder

#### Using the program
To delete the content in the 'output' folder:
'py -c "import pathlib, shutil; p=pathlib.Path('output'); [shutil.rmtree(x, ignore_errors=True) if x.is_dir() else x.unlink(missing_ok=True) for x in p.iterdir()] if p.exists() else None"'

To run the program, use the 'Makefile' or use this:
'py restamp.py -i input -o output --preset nikon --font ".\fonts\VCR_OSD_MONO_1.001.ttf"' 

##### Makefile (optional)
For users on Linux, macOS, or Windows (via WSL), a Makefile is included...not tested yet though I'm on windows HEHE
