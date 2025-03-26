from subprocess import run
from tf.core.helpers import console
from tf.core.files import (
    dirContents,
    dirExists,
    dirRemove,
    dirCopy,
    initTree,
    fileExists,
    extNm,
    fileRemove,
    expanduser,
)
from tff.convert.iiif import FILE_NOT_FOUND


ORG = "HuygensING"
REPO = "vangogh"
BACKEND = "github"
LOGO = "logo"
PAGES = "pages"
REPODIR = expanduser(f"~/{BACKEND}/{ORG}/{REPO}")
SCANDIR = f"{REPODIR}/scans"
THUMBDIR = f"{REPODIR}/thumb"
THUMBLOGODIR = f"{THUMBDIR}/{LOGO}"

SCAN_QUALITY = "15%"
SCAN_RESIZE = "35%"
SCAN_COMMAND = "/opt/homebrew/bin/magick"

SCAN_OPTIONS = ["-quality", SCAN_QUALITY, "-resize", SCAN_RESIZE]
SCAN_EXT = ("png", "jpg")

SIZES_COMMAND = "/opt/homebrew/bin/identify"
SIZES_OPTIONS = ["-ping", "-format", "%w %h"]

DS_STORE = ".DS_Store"


class Scans:
    def __init__(self, silent=False, force=False):
        scanDir = "scans"
        srcImageDir = f"{REPODIR}/{scanDir}"
        pageInDir = f"{srcImageDir}/{PAGES}"
        logoInDir = f"{srcImageDir}/{LOGO}"

        self.srcImageDir = srcImageDir
        self.pageInDir = pageInDir
        self.logoInDir = logoInDir

        self.silent = silent
        self.force = force
        self.errors = {}
        self.error = False

    def process(self, force=False):
        if self.error:
            return

        if force is None:
            force = self.force

        silent = self.silent
        srcImageDir = self.srcImageDir
        logoInDir = self.logoInDir

        plabel = "originals"
        dlabel = "thumbnails"

        srcDir = f"{srcImageDir}/{PAGES}"
        dstDir = f"{THUMBDIR}/{PAGES}"
        sizesFileThumb = f"{THUMBDIR}/sizes_{PAGES}.tsv"
        sizesFileScans = f"{SCANDIR}/sizes_{PAGES}.tsv"

        if force or not dirExists(THUMBLOGODIR):
            dirRemove(THUMBLOGODIR)
            dirCopy(logoInDir, THUMBLOGODIR)

        if force or not dirExists(dstDir):
            self.doThumb(srcDir, dstDir, *SCAN_EXT, plabel, dlabel)
        else:
            if not silent:
                console(f"Already present: {dlabel} ({PAGES})")

        if force or not fileExists(sizesFileThumb):
            self.doSizes(dstDir, SCAN_EXT[1], sizesFileThumb, dlabel)
        else:
            if not silent:
                console(f"Already present: sizes file {dlabel} ({PAGES})")

        if force or not fileExists(sizesFileScans):
            self.doSizes(srcDir, SCAN_EXT[0], sizesFileScans, plabel)
        else:
            if not silent:
                console(f"Already present: sizes file {plabel} ({PAGES})")

        for folder, label, ext in (
            (srcDir, plabel, SCAN_EXT[0]),
            (dstDir, dlabel, SCAN_EXT[1]),
        ):
            notFound = f"{FILE_NOT_FOUND}.{ext}"
            files = [
                f
                for f in dirContents(folder)[0]
                if f not in {DS_STORE, notFound} and extNm(f) == ext
            ]
            nFiles = len(files)
            console(f"{label}: {nFiles}")

    def doSizes(self, imDir, ext, sizesFile, label):
        if self.error:
            return

        silent = self.silent
        fileRemove(sizesFile)

        fileNames = dirContents(imDir)[0]
        items = []

        for fileName in sorted(fileNames):
            if fileName == DS_STORE:
                continue

            thisExt = extNm(fileName)

            if thisExt != ext:
                continue

            base = fileName.removesuffix(f".{thisExt}")
            items.append((base, f"{imDir}/{fileName}"))

        console(f"\tGet sizes of {len(items)} {label} ({PAGES})")
        j = 0
        nItems = len(items)

        sizes = []

        for i, (base, fromFile) in enumerate(sorted(items)):
            if j == 100:
                perc = int(round(i * 100 / nItems))

                if not silent:
                    console(f"\t\t{perc:>3}% done")

                j = 0

            status = run(
                [SIZES_COMMAND] + SIZES_OPTIONS + [fromFile], capture_output=True
            )
            j += 1

            if status.returncode != 0:
                console(status.stderr.decode("utf-8"), error=True)
            else:
                (w, h) = status.stdout.decode("utf-8").strip().split()
                sizes.append((base, w, h))

        perc = 100

        if not silent:
            console(f"\t\t{perc:>3}% done")

        with open(sizesFile, "w") as fh:
            fh.write("file\twidth\theight\n")

            for file, w, h in sizes:
                fh.write(f"{file}\t{w}\t{h}\n")

    def doThumb(self, fromDir, toDir, extIn, extOut, plabel, dlabel):
        if self.error:
            return

        silent = self.silent
        initTree(toDir, fresh=True)

        fileNames = dirContents(fromDir)[0]
        items = []

        for fileName in sorted(fileNames):
            if fileName == DS_STORE:
                continue

            thisExt = extNm(fileName)
            base = fileName.removesuffix(f".{thisExt}")

            if thisExt != extIn:
                continue

            items.append((base, f"{fromDir}/{fileName}", f"{toDir}/{base}.{extOut}"))

        console(f"\tConvert {len(items)} {plabel} to {dlabel} ({PAGES})")

        j = 0
        nItems = len(items)

        for i, (base, fromFile, toFile) in enumerate(sorted(items)):
            if j == 100:
                perc = int(round(i * 100 / nItems))

                if not silent:
                    console(f"\t\t{perc:>3}% done")

                j = 0

            run([SCAN_COMMAND] + [fromFile] + SCAN_OPTIONS + [toFile])
            j += 1

        perc = 100
        if not silent:
            console(f"\t\t{perc:>3}% done")
