"""Source cleanup and finished-folder merge helpers."""

from __future__ import annotations

import shutil
from pathlib import Path


def cleanup_empty_source_folder(source_root: Path, destination_root: Path) -> bool:
    """Remove empty source directories after processing."""

    try:
        source_resolved = source_root.resolve()
        destination_resolved = destination_root.resolve()
    except OSError:
        source_resolved = source_root
        destination_resolved = destination_root

    if source_resolved == destination_resolved:
        print()
        print("SOURCE AND DESTINATION ARE THE SAME FOLDER.")
        print("The folder will be preserved.")
        return True

    if not source_root.exists():
        return True

    directories = []

    try:
        for path in source_root.rglob("*"):
            if path.is_dir():
                directories.append(path)
    except OSError:
        pass

    directories.sort(key=lambda path: len(path.parts), reverse=True)

    for directory in directories:
        try:
            directory.rmdir()
            print(f"Removed empty folder: {directory}")
        except OSError:
            pass

    try:
        source_root.rmdir()
        print()
        print("Source folder deleted because it is empty.")
        return True
    except OSError:
        print()
        print("Source folder still contains files.")
        print("It was not deleted.")
        return False


def move_finished_folder(finished_folder: Path, destination_root: Path) -> bool:
    """Move/merge the finished media folder into destination_root."""

    if not finished_folder.exists():
        print()
        print("[ERROR] Finished folder does not exist:")
        print(f"        {finished_folder}")
        return False

    if not finished_folder.is_dir():
        print()
        print("[ERROR] Finished path is not a directory:")
        print(f"        {finished_folder}")
        return False

    destination_root.mkdir(parents=True, exist_ok=True)
    destination = destination_root / finished_folder.name

    try:
        same_directory = finished_folder.resolve() == destination.resolve()
    except OSError:
        same_directory = finished_folder == destination

    if same_directory:
        print()
        print("Finished folder is already in the destination.")
        print(f"LOCATION: {finished_folder}")
        return True

    if not destination.exists():
        print()
        print("=" * 70)
        print("MOVING FINISHED FOLDER")
        print("=" * 70)
        print(f"SOURCE      : {finished_folder}")
        print(f"DESTINATION : {destination}")

        try:
            shutil.move(str(finished_folder), str(destination))
            print()
            print("Finished folder moved successfully.")
            return True
        except OSError as error:
            print()
            print("[ERROR] Could not move finished folder.")
            print(f"        {error}")
            return False

    print()
    print("=" * 70)
    print("MERGING FINISHED FOLDER")
    print("=" * 70)
    print("The destination folder already exists.")
    print("Its contents will be merged instead of replacing it.")
    print()
    print(f"SOURCE      : {finished_folder}")
    print(f"DESTINATION : {destination}")

    source_files_remaining = False
    source_items = list(finished_folder.rglob("*"))
    source_items.sort(key=lambda path: (not path.is_dir(), len(path.parts)))

    for source_item in source_items:
        relative_path = source_item.relative_to(finished_folder)
        destination_item = destination / relative_path

        if source_item.is_dir():
            try:
                destination_item.mkdir(parents=True, exist_ok=True)
            except OSError as error:
                print()
                print("[WARNING] Could not create directory:")
                print(f"          {destination_item}")
                print(f"          {error}")
            continue

        destination_item.parent.mkdir(parents=True, exist_ok=True)

        if destination_item.exists():
            print()
            print("[WARNING] Destination already exists:")
            print(f"          {destination_item}")
            print("          Skipping source file.")
            source_files_remaining = True
            continue

        print()
        print(f"MOVE FILE : {source_item}")
        print(f"         -> {destination_item}")

        try:
            shutil.move(str(source_item), str(destination_item))
        except OSError as error:
            print()
            print("[WARNING] Could not move file:")
            print(f"          {source_item}")
            print(f"          {error}")
            source_files_remaining = True

    directories = []

    try:
        for path in finished_folder.rglob("*"):
            if path.is_dir():
                directories.append(path)
    except OSError:
        pass

    directories.sort(key=lambda path: len(path.parts), reverse=True)

    for directory in directories:
        try:
            directory.rmdir()
        except OSError:
            pass

    try:
        finished_folder.rmdir()
    except OSError:
        source_files_remaining = True

    if source_files_remaining:
        print()
        print("Finished folder still contains files.")
        print("It was not deleted.")
        return False

    print()
    print("Finished folder merged successfully.")
    return True
