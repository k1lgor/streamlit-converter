import os
import shutil
import tempfile
from typing import Union

import ffmpeg
import streamlit as st
from PIL import Image
from werkzeug.utils import secure_filename


def convert_image(input_file, output_format):
    try:
        # Validate input file
        if not input_file:
            st.error("No input file provided.")
            return None

        # Check file size before processing
        input_file.seek(0, os.SEEK_END)
        file_size = input_file.tell()
        input_file.seek(0)

        if file_size > 10 * 1024 * 1024:  # 10 MB limit
            st.error("File size exceeds the limit of 10 MB.")
            return None

        img = Image.open(input_file)

        # Validate image dimensions
        max_dimensions = (10000, 10000)  # Prevent extremely large images
        if img.width > max_dimensions[0] or img.height > max_dimensions[1]:
            st.error(
                f"Image dimensions exceed {max_dimensions[0]}x{max_dimensions[1]} pixels."
            )
            return None

        # Use the original file name with the new extension
        input_name, _ = os.path.splitext(input_file.name)
        output_filename = f"{input_name}.{output_format.lower()}"

        # Convert to RGB if the mode is not compatible with the output format
        if output_format.upper() == "JPEG" and img.mode != "RGB":
            img = img.convert("RGB")

        # Save with best quality (JPEG quality=95, WebP quality=90)
        save_params = {"quality": 95} if output_format.upper() == "JPEG" else {}
        save_params = (
            {"quality": 90} if output_format.upper() == "WEBP" else save_params
        )
        img.save(output_filename, **save_params)

        return output_filename
    except Image.UnidentifiedImageError:
        st.error("Unable to identify image file. Please check the file format.")
        return None
    except PermissionError:
        st.error("Permission denied. Please check file permissions.")
        return None
    except Exception as e:
        st.error(f"Error converting image: {e}")
        return None


# Function to convert videos using ffmpeg with best quality by default
def convert_video(
    input_file: Union[st.runtime.uploaded_file_manager.UploadedFile, str],
    output_format: str,
):
    try:
        # Use temporary directory for file handling
        with tempfile.TemporaryDirectory() as tmpdir:
            # Secure filename generation
            input_filename = secure_filename(input_file.name)
            input_path = os.path.join(tmpdir, input_filename)

            with open(input_path, "wb") as f:
                f.write(input_file.read())

            # Validate file size
            file_size = os.path.getsize(input_path)
            if file_size > 10 * 1024 * 1024:  # 10 MB limit
                st.error("File size exceeds the limit of 10 MB.")
                return None

            # Generate output filename
            output_filename = (
                f"{os.path.splitext(input_filename)[0]}.{output_format.lower()}"
            )
            output_path = os.path.join(tmpdir, output_filename)

            # Conversion with progress tracking
            with st.spinner(f"Converting video to {output_format}..."):
                stream = ffmpeg.input(input_path)
                stream = ffmpeg.output(
                    stream,
                    output_path,
                    **{"c:v": "libx264", "preset": "slow", "crf": 18}
                    if output_format.lower() == "mp4"
                    else {},
                    **{"c:v": "gif"} if output_format.lower() == "gif" else {},
                    **{
                        "c:v": "libx264",
                        "preset": "slow",
                        "crf": 18,
                        "format": "matroska",
                    }
                    if output_format.lower() == "mkv"
                    else {},
                    **{"c:v": "libvpx-vp9", "crf": 30}
                    if output_format.lower() == "webm"
                    else {},
                    **{"c:v": "flv"} if output_format.lower() == "flv" else {},
                    **{"c:v": "wmv2"} if output_format.lower() == "wmv" else {},
                    **{"c:v": "libx264", "preset": "slow", "crf": 18, "format": "mp4"}
                    if output_format.lower() == "m4v"
                    else {},
                )
                ffmpeg.run(stream)

            # Copy file to current directory for download
            final_output_path = os.path.join(os.getcwd(), output_filename)
            shutil.copy(output_path, final_output_path)

            return final_output_path

    except ffmpeg.Error as e:
        st.error(f"FFmpeg error: {e.stderr}")
        return None
    except Exception as e:
        st.error(f"Error converting video: {e}")
        return None


# Function to create a download button and delete the file after download
def create_download_button(file_path, label="Download"):
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        st.download_button(
            label=label, data=data, file_name=os.path.basename(file_path), mime=None
        )

        # Delete the file after it has been downloaded
        os.remove(file_path)
    except Exception as e:
        st.error(f"Error while handling file: {e}")


# Main Streamlit App
def main():
    st.title("Image/Video Converter")

    # Sidebar for selecting conversion type
    conversion_type = st.sidebar.selectbox("Select Conversion Type", ["Image", "Video"])

    # File uploader
    uploaded_file = st.file_uploader(
        "Upload a file",
        type=[
            "png",
            "jpg",
            "jpeg",
            "bmp",
            "ico",
            "webp",
            "mp4",
            "avi",
            "mov",
            "mkv",
            "webm",
            "flv",
            "wmv",
            "m4v",
            "gif",
        ],
    )

    if uploaded_file is not None:
        st.write(f"Uploaded file: {uploaded_file.name}")

        if conversion_type == "Image":
            output_format = st.selectbox(
                "Convert to:", ["PNG", "JPEG", "GIF", "WebP", "BMP", "ICO"]
            )
            if st.button("Convert"):
                result = convert_image(uploaded_file, output_format)
                if result:
                    st.success("Conversion successful!")
                    create_download_button(result, label="Download Converted Image")

        elif conversion_type == "Video":
            output_format = st.selectbox(
                "Convert to:", ["MP4", "AVI", "GIF", "MKV", "WEBM", "FLV", "WMV", "M4V"]
            )
            if st.button("Convert"):
                result = convert_video(uploaded_file, output_format)
                if result:
                    st.success("Conversion successful!")
                    create_download_button(result, label="Download Converted Video")


if __name__ == "__main__":
    main()
