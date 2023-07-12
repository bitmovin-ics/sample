import time

from bitmovin_api_sdk import BitmovinApi
from bitmovin_api_sdk import S3Input, S3Output
from bitmovin_api_sdk import Encoding, CloudRegion
from bitmovin_api_sdk import EncodingOutput, AclEntry, AclPermission
from bitmovin_api_sdk import DolbyVisionInputStream, Stream, StreamInput, MuxingStream, StreamMode
from bitmovin_api_sdk import DolbyAtmosAudioConfiguration, DolbyAtmosLoudnessControl, DolbyAtmosMeteringMode
from bitmovin_api_sdk import DolbyAtmosDialogueIntelligence, DolbyAtmosIngestInputStream, DolbyAtmosInputFormat
from bitmovin_api_sdk import DolbyDigitalPlusAudioConfiguration, DolbyDigitalPlusChannelLayout
from bitmovin_api_sdk import DolbyDigitalAudioConfiguration, DolbyDigitalChannelLayout
from bitmovin_api_sdk import AacAudioConfiguration, AacChannelLayout
from bitmovin_api_sdk import IngestInputStream, StreamSelectionMode
from bitmovin_api_sdk import H265VideoConfiguration, CodecConfigType, PresetConfiguration
from bitmovin_api_sdk import H265DynamicRangeFormat
from bitmovin_api_sdk import Fmp4Muxing
from bitmovin_api_sdk import DashManifest, Period, VideoAdaptationSet, AudioAdaptationSet, Label
from bitmovin_api_sdk import DashFmp4Representation, DashRepresentationType, DashRepresentationTypeMode
from bitmovin_api_sdk import HlsManifest, HlsVersion, AudioMediaInfo, StreamInfo
from bitmovin_api_sdk import MessageType, StartEncodingRequest, ManifestResource, ManifestGenerator
from bitmovin_api_sdk import Status

TEST_ITEM = "dv-embedded-with-atmos-ddp-dd-aac"

API_KEY = '<INSERT YOUR API KEY>'
ORG_ID = '<INSERT YOUR ORG ID>'

S3_INPUT_ACCESS_KEY = '<INSERT_YOUR_ACCESS_KEY>'
S3_INPUT_SECRET_KEY = '<INSERT_YOUR_SECRET_KEY>'
S3_INPUT_BUCKET_NAME = '<INSERT_YOUR_BUCKET_NAME>'

S3_OUTPUT_ACCESS_KEY = '<INSERT_YOUR_ACCESS_KEY>'
S3_OUTPUT_SECRET_KEY = '<INSERT_YOUR_SECRET_KEY>'
S3_OUTPUT_BUCKET_NAME = '<INSERT_YOUR_BUCKET_NAME>'

# from https://opencontent.netflix.com/
# Input file for Dolby Vision (Video Only))
INPUT_PATH_FOR_DOLBY_VISION = "netflix-opencontent/SolLevante/imf/VIDEO_e4da5fcd-5ffc-4713-bcdd-95ea579d790b.mxf"

# Input file for Dolby Atmos
INPUT_PATH_FOR_DOLBY_ATMOS_ADM = "netflix-opencontent/SolLevante/atmos-adm/sollevante_lp_v01_DAMF_Nearfield_48k_24b_24.wav"

# Input file for non-Dolby Atmos (Stereo PCM Audio)
INPUT_PATH_FOR_STEREO_PCM = "netflix-opencontent/SolLevante/imf/AUDIO_4467fc2f-2536-44ba-b1f9-010e0ae3f6b1.mxf"

OUTPUT_BASE_PATH = 'output/{}/'.format(TEST_ITEM)

bitmovin_api = BitmovinApi(api_key=API_KEY, tenant_org_id=ORG_ID)

video_encoding_profiles = [
    dict(height=360, bitrate=1_000_000, level=None, mode=StreamMode.STANDARD, dynamic_range=H265DynamicRangeFormat.DOLBY_VISION)
]

audio_encoding_profiles = [
    # dict(codec="atmos", bitrate=448000, rate=48_000),
    dict(codec="dolby-digital-plus", bitrate=192000, rate=48_000),
    # dict(codec="dolby-digital", bitrate=192000, rate=48_000),
    # dict(codec="aac", bitrate=192000, rate=48_000)
]


def main():
    # === Input and Output definition ===
    s3_input = bitmovin_api.encoding.inputs.s3.create(
        s3_input=S3Input(
            access_key=S3_INPUT_ACCESS_KEY,
            secret_key=S3_INPUT_SECRET_KEY,
            bucket_name=S3_INPUT_BUCKET_NAME,
            name='Test S3 Input'))
    s3_output = bitmovin_api.encoding.outputs.s3.create(
        s3_output=S3Output(
            access_key=S3_OUTPUT_ACCESS_KEY,
            secret_key=S3_OUTPUT_SECRET_KEY,
            bucket_name=S3_OUTPUT_BUCKET_NAME,
            name='Test S3 Output'))

    # === Encoding definition ===
    encoding = bitmovin_api.encoding.encodings.create(
        encoding=Encoding(
            name='{}'.format(TEST_ITEM),
            cloud_region=CloudRegion.AWS_AP_NORTHEAST_1,
            encoder_version='STABLE'))

    # === Input Stream definition ===
    video_ingest_input_stream = bitmovin_api.encoding.encodings.input_streams.dolby_vision.create(
        encoding_id=encoding.id,
        dolby_vision_input_stream=DolbyVisionInputStream(
            input_id=s3_input.id,
            video_input_path=INPUT_PATH_FOR_DOLBY_VISION))
    audio_ingest_input_stream_for_atmos = bitmovin_api.encoding.encodings.input_streams.dolby_atmos.create(
        encoding_id=encoding.id,
        dolby_atmos_ingest_input_stream=DolbyAtmosIngestInputStream(
            input_id=s3_input.id,
            input_path=INPUT_PATH_FOR_DOLBY_ATMOS_ADM,
            input_format=DolbyAtmosInputFormat.ADM))
    audio_ingest_input_stream_for_non_atmos_stereo = bitmovin_api.encoding.encodings.input_streams.ingest.create(
        encoding_id=encoding.id,
        ingest_input_stream=IngestInputStream(
            input_id=s3_input.id,
            input_path=INPUT_PATH_FOR_STEREO_PCM,
            selection_mode=StreamSelectionMode.AUDIO_RELATIVE,
            position=0))
    video_input_stream = StreamInput(input_stream_id=video_ingest_input_stream.id)
    audio_input_stream_for_atmos = StreamInput(input_stream_id=audio_ingest_input_stream_for_atmos.id)
    audio_input_stream_for_non_atmos_stereo = StreamInput(input_stream_id=audio_ingest_input_stream_for_non_atmos_stereo.id)

    # === Video Profile definition ===
    for video_profile in video_encoding_profiles:

        # Create Video Codec Configuration
        h265_codec = bitmovin_api.encoding.configurations.video.h265.create(
            h265_video_configuration=H265VideoConfiguration(
                name='Sample video codec configuration',
                height=video_profile.get("height"),
                bitrate=video_profile.get("bitrate"),
                bufsize=video_profile.get("bitrate") * 4,
                level=video_profile.get("level"),
                dynamic_range_format=video_profile.get("dynamic_range"),
                preset_configuration=PresetConfiguration.VOD_HIGH_QUALITY))

        # Create Video Stream
        h265_stream = bitmovin_api.encoding.encodings.streams.create(
            encoding_id=encoding.id,
            stream=Stream(
                codec_config_id=h265_codec.id,
                input_streams=[video_input_stream],
                name=f"Stream H265 {video_profile.get('height')}p",
                mode=video_profile.get('mode')))

        # Create Fmp4 muxing output path
        video_muxing_output = EncodingOutput(
            output_id=s3_output.id,
            output_path=OUTPUT_BASE_PATH + f"video/{video_profile.get('height')}",
            acl=[AclEntry(permission=AclPermission.PUBLIC_READ)])

        # Create Fmp4 muxing
        bitmovin_api.encoding.encodings.muxings.fmp4.create(
            encoding_id=encoding.id,
            fmp4_muxing=Fmp4Muxing(
                segment_length=6,
                segment_naming='segment_%number%.m4s',
                init_segment_name='init.mp4',
                streams=[MuxingStream(stream_id=h265_stream.id)],
                outputs=[video_muxing_output],
                name=f"Video FMP4 Muxing {video_profile.get('height')}p"))

    # === Audio Profile definition ===
    for audio_profile in audio_encoding_profiles:
        audio_codec = None
        audio_stream_name = None
        audio_input_stream = None

        # Create Audio Codec Configuration
        if audio_profile.get('codec') == 'atmos':
            audio_codec = bitmovin_api.encoding.configurations.audio.dolby_atmos.create(
                dolby_atmos_audio_configuration=DolbyAtmosAudioConfiguration(
                    bitrate=audio_profile.get("bitrate"),
                    rate=audio_profile.get("rate"),
                    loudness_control=DolbyAtmosLoudnessControl(
                        metering_mode=DolbyAtmosMeteringMode.ITU_R_BS_1770_4,
                        dialogue_intelligence=DolbyAtmosDialogueIntelligence.ENABLED,
                        speech_threshold=15)))
            audio_stream_name = f"Audio Stream Atmos {audio_profile.get('bitrate') / 1000:.0f}kbps"
            audio_input_stream = audio_input_stream_for_atmos
        elif audio_profile.get('codec') == 'dolby-digital-plus':
            audio_codec = bitmovin_api.encoding.configurations.audio.dolby_digital_plus.create(
                dolby_digital_plus_audio_configuration=DolbyDigitalPlusAudioConfiguration(
                    bitrate=audio_profile.get("bitrate"),
                    rate=audio_profile.get("rate"),
                    channel_layout=DolbyDigitalPlusChannelLayout.CL_STEREO))
            audio_stream_name = f"Audio Stream Dolby Digital Plus {audio_profile.get('bitrate') / 1000:.0f}kbps"
            audio_input_stream = audio_input_stream_for_non_atmos_stereo
        elif audio_profile.get('codec') == 'dolby-digital':
            audio_codec = bitmovin_api.encoding.configurations.audio.dolby_digital.create(
                dolby_digital_audio_configuration=DolbyDigitalAudioConfiguration(
                    bitrate=audio_profile.get("bitrate"),
                    rate=audio_profile.get("rate"),
                    channel_layout=DolbyDigitalChannelLayout.CL_STEREO))
            audio_stream_name = f"Audio Stream Dolby Digital {audio_profile.get('bitrate') / 1000:.0f}kbps"
            audio_input_stream = audio_input_stream_for_non_atmos_stereo
        elif audio_profile.get('codec') == 'aac':
            audio_codec = bitmovin_api.encoding.configurations.audio.aac.create(
                aac_audio_configuration=AacAudioConfiguration(
                    bitrate=audio_profile.get("bitrate"),
                    rate=audio_profile.get("rate"),
                    channel_layout=AacChannelLayout.CL_STEREO))
            audio_stream_name = f"Audio Stream AAC {audio_profile.get('bitrate') / 1000:.0f}kbps"
            audio_input_stream = audio_input_stream_for_non_atmos_stereo

        # Create Audio Stream
        audio_stream = bitmovin_api.encoding.encodings.streams.create(
            encoding_id=encoding.id,
            stream=Stream(
                codec_config_id=audio_codec.id,
                input_streams=[audio_input_stream],
                name=audio_stream_name,
                mode=StreamMode.STANDARD))

        # Create Fmp4 muxing output path
        audio_muxing_output = EncodingOutput(
            output_id=s3_output.id,
            output_path=OUTPUT_BASE_PATH + f"audio/{audio_profile.get('codec')}/{audio_profile.get('bitrate')}",
            acl=[AclEntry(permission=AclPermission.PUBLIC_READ)])

        # Create Fmp4 muxing
        bitmovin_api.encoding.encodings.muxings.fmp4.create(
            encoding_id=encoding.id,
            fmp4_muxing=Fmp4Muxing(
                segment_length=6,
                segment_naming='segment_%number%.m4s',
                init_segment_name='init.mp4',
                streams=[MuxingStream(stream_id=audio_stream.id)],
                outputs=[audio_muxing_output],
                name=f"Audio FMP4 Muxing {audio_profile.get('bitrate')/1000:.0f}kbps"))

    # === Start Encoding settings together with DASh & HLS Manifest definition ===
    dash_manifest = _create_dash_manifest(encoding_id=encoding.id, output=s3_output, output_path=OUTPUT_BASE_PATH)
    hls_manifest = _create_hls_manifest(encoding_id=encoding.id, output=s3_output, output_path=OUTPUT_BASE_PATH)

    start_encoding_request = StartEncodingRequest(
        vod_dash_manifests=[ManifestResource(manifest_id=dash_manifest.id)],
        vod_hls_manifests=[ManifestResource(manifest_id=hls_manifest.id)],
        manifest_generator=ManifestGenerator.V2
    )
    _execute_encoding(encoding=encoding, start_encoding_request=start_encoding_request)


def _execute_encoding(encoding, start_encoding_request):
    bitmovin_api.encoding.encodings.start(encoding_id=encoding.id, start_encoding_request=start_encoding_request)

    task = _wait_for_enoding_to_finish(encoding_id=encoding.id)

    while task.status is not Status.FINISHED and task.status is not Status.ERROR:
        task = _wait_for_enoding_to_finish(encoding_id=encoding.id)

    if task.status is Status.ERROR:
        _log_task_errors(task=task)
        raise Exception("Encoding failed")

    print("Encoding finished successfully")


def _create_dash_manifest(encoding_id, output, output_path):
    manifest_output = EncodingOutput(output_id=output.id,
                                     output_path=output_path,
                                     acl=[AclEntry(permission=AclPermission.PUBLIC_READ)])
    dash_manifest = bitmovin_api.encoding.manifests.dash.create(
        dash_manifest=DashManifest(
            manifest_name='stream.mpd',
            outputs=[manifest_output],
            name='DASH Manifest'))
    period = bitmovin_api.encoding.manifests.dash.periods.create(
        manifest_id=dash_manifest.id,
        period=Period())
    video_adaptation_set = bitmovin_api.encoding.manifests.dash.periods.adaptationsets.video.create(
        video_adaptation_set=VideoAdaptationSet(),
        manifest_id=dash_manifest.id,
        period_id=period.id)

    audio_adaptation_set_for_atmos = None
    audio_adaptation_set_for_dolby_digital_plus = None
    audio_adaptation_set_for_dolby_digital = None
    audio_adaptation_set_for_aac = None
    for audio_profile in audio_encoding_profiles:
        if audio_profile.get('codec') == 'atmos':
            audio_adaptation_set_for_atmos = bitmovin_api.encoding.manifests.dash.periods.adaptationsets.audio.create(
                audio_adaptation_set=AudioAdaptationSet(lang='en', labels=[Label(value='atmos')]),
                manifest_id=dash_manifest.id,
                period_id=period.id)
        elif audio_profile.get('codec') == 'dolby-digital-plus':
            audio_adaptation_set_for_dolby_digital_plus = bitmovin_api.encoding.manifests.dash.periods.adaptationsets.audio.create(
                audio_adaptation_set=AudioAdaptationSet(lang='en', labels=[Label(value='ddp')]),
                manifest_id=dash_manifest.id,
                period_id=period.id)
        elif audio_profile.get('codec') == 'dolby-digital':
            audio_adaptation_set_for_dolby_digital = bitmovin_api.encoding.manifests.dash.periods.adaptationsets.audio.create(
                audio_adaptation_set=AudioAdaptationSet(lang='en', labels=[Label(value='dd')]),
                manifest_id=dash_manifest.id,
                period_id=period.id)
        elif audio_profile.get('codec') == 'aac':
            audio_adaptation_set_for_aac = bitmovin_api.encoding.manifests.dash.periods.adaptationsets.audio.create(
                audio_adaptation_set=AudioAdaptationSet(lang='en', labels=[Label(value='aac')]),
                manifest_id=dash_manifest.id,
                period_id=period.id)

    fmp4_muxings = bitmovin_api.encoding.encodings.muxings.fmp4.list(encoding_id=encoding_id)
    for muxing in fmp4_muxings.items:
        stream = bitmovin_api.encoding.encodings.streams.get(
            encoding_id=encoding_id, stream_id=muxing.streams[0].stream_id)

        if 'PER_TITLE_TEMPLATE' in stream.mode.value:
            continue

        codec = bitmovin_api.encoding.configurations.type.get(configuration_id=stream.codec_config_id)
        segment_path = _remove_output_base_path(muxing.outputs[0].output_path)

        if codec.type == CodecConfigType.H265:
            bitmovin_api.encoding.manifests.dash.periods.adaptationsets.representations.fmp4.create(
                manifest_id=dash_manifest.id,
                period_id=period.id,
                adaptationset_id=video_adaptation_set.id,
                dash_fmp4_representation=DashFmp4Representation(
                    encoding_id=encoding_id,
                    muxing_id=muxing.id,
                    type_=DashRepresentationType.TEMPLATE,
                    mode=DashRepresentationTypeMode.TEMPLATE_REPRESENTATION,
                    segment_path=segment_path))
        elif codec.type == CodecConfigType.DOLBY_ATMOS:
            bitmovin_api.encoding.manifests.dash.periods.adaptationsets.representations.fmp4.create(
                manifest_id=dash_manifest.id,
                period_id=period.id,
                adaptationset_id=audio_adaptation_set_for_atmos.id,
                dash_fmp4_representation=DashFmp4Representation(
                    encoding_id=encoding_id,
                    muxing_id=muxing.id,
                    type_=DashRepresentationType.TEMPLATE,
                    mode=DashRepresentationTypeMode.TEMPLATE_REPRESENTATION,
                    segment_path=segment_path))
        elif codec.type == CodecConfigType.DDPLUS:
            bitmovin_api.encoding.manifests.dash.periods.adaptationsets.representations.fmp4.create(
                manifest_id=dash_manifest.id,
                period_id=period.id,
                adaptationset_id=audio_adaptation_set_for_dolby_digital_plus.id,
                dash_fmp4_representation=DashFmp4Representation(
                    encoding_id=encoding_id,
                    muxing_id=muxing.id,
                    type_=DashRepresentationType.TEMPLATE,
                    mode=DashRepresentationTypeMode.TEMPLATE_REPRESENTATION,
                    segment_path=segment_path))
        elif codec.type == CodecConfigType.DD:
            bitmovin_api.encoding.manifests.dash.periods.adaptationsets.representations.fmp4.create(
                manifest_id=dash_manifest.id,
                period_id=period.id,
                adaptationset_id=audio_adaptation_set_for_dolby_digital.id,
                dash_fmp4_representation=DashFmp4Representation(
                    encoding_id=encoding_id,
                    muxing_id=muxing.id,
                    type_=DashRepresentationType.TEMPLATE,
                    mode=DashRepresentationTypeMode.TEMPLATE_REPRESENTATION,
                    segment_path=segment_path))
        elif codec.type == CodecConfigType.AAC:
            bitmovin_api.encoding.manifests.dash.periods.adaptationsets.representations.fmp4.create(
                manifest_id=dash_manifest.id,
                period_id=period.id,
                adaptationset_id=audio_adaptation_set_for_aac.id,
                dash_fmp4_representation=DashFmp4Representation(
                    encoding_id=encoding_id,
                    muxing_id=muxing.id,
                    type_=DashRepresentationType.TEMPLATE,
                    mode=DashRepresentationTypeMode.TEMPLATE_REPRESENTATION,
                    segment_path=segment_path))
    return dash_manifest


def _create_hls_manifest(encoding_id, output, output_path):
    manifest_output = EncodingOutput(output_id=output.id,
                                     output_path=output_path,
                                     acl=[AclEntry(permission=AclPermission.PUBLIC_READ)])

    hls_manifest = bitmovin_api.encoding.manifests.hls.create(
        hls_manifest=HlsManifest(
            manifest_name='stream.m3u8',
            outputs=[manifest_output],
            name='HLS Manifest',
            hls_master_playlist_version=HlsVersion.HLS_V8,
            hls_media_playlist_version=HlsVersion.HLS_V8))

    fmp4_muxings = bitmovin_api.encoding.encodings.muxings.fmp4.list(encoding_id=encoding_id)
    for muxing in fmp4_muxings.items:
        stream = bitmovin_api.encoding.encodings.streams.get(
            encoding_id=encoding_id, stream_id=muxing.streams[0].stream_id)

        if 'PER_TITLE_TEMPLATE' in stream.mode.value:
            continue

        codec = bitmovin_api.encoding.configurations.type.get(configuration_id=stream.codec_config_id)
        segment_path = _remove_output_base_path(muxing.outputs[0].output_path)

        if codec.type == CodecConfigType.H265:
            video_codec = bitmovin_api.encoding.configurations.video.h265.get(configuration_id=stream.codec_config_id)
            bitmovin_api.encoding.manifests.hls.streams.create(
                manifest_id=hls_manifest.id,
                stream_info=StreamInfo(
                    audio='audio',
                    closed_captions='NONE',
                    segment_path=segment_path,
                    uri='video_{}.m3u8'.format(video_codec.bitrate),
                    encoding_id=encoding_id,
                    stream_id=stream.id,
                    muxing_id=muxing.id))
        elif codec.type == CodecConfigType.DOLBY_ATMOS:
            audio_codec = bitmovin_api.encoding.configurations.audio.dolby_atmos.get(
                configuration_id=stream.codec_config_id)
            bitmovin_api.encoding.manifests.hls.media.audio.create(
                manifest_id=hls_manifest.id,
                audio_media_info=AudioMediaInfo(
                    name='Atmos',
                    group_id='audio',
                    language='en',
                    segment_path=segment_path,
                    encoding_id=encoding_id,
                    stream_id=stream.id,
                    muxing_id=muxing.id,
                    uri='atmos_audio_{}.m3u8'.format(audio_codec.bitrate)))
        elif codec.type == CodecConfigType.DDPLUS:
            audio_codec = bitmovin_api.encoding.configurations.audio.dolby_digital_plus.get(
                configuration_id=stream.codec_config_id)
            bitmovin_api.encoding.manifests.hls.media.audio.create(
                manifest_id=hls_manifest.id,
                audio_media_info=AudioMediaInfo(
                    name='Dolby Digital Plus',
                    group_id='audio',
                    language='en',
                    segment_path=segment_path,
                    encoding_id=encoding_id,
                    stream_id=stream.id,
                    muxing_id=muxing.id,
                    uri='ddp_audio_{}.m3u8'.format(audio_codec.bitrate)))
        elif codec.type == CodecConfigType.DD:
            audio_codec = bitmovin_api.encoding.configurations.audio.dolby_digital.get(
                configuration_id=stream.codec_config_id)
            bitmovin_api.encoding.manifests.hls.media.audio.create(
                manifest_id=hls_manifest.id,
                audio_media_info=AudioMediaInfo(
                    name='Dolby Digital',
                    group_id='audio',
                    language='en',
                    segment_path=segment_path,
                    encoding_id=encoding_id,
                    stream_id=stream.id,
                    muxing_id=muxing.id,
                    uri='dd_audio_{}.m3u8'.format(audio_codec.bitrate)))
        elif codec.type == CodecConfigType.AAC:
            audio_codec = bitmovin_api.encoding.configurations.audio.aac.get(
                configuration_id=stream.codec_config_id)
            bitmovin_api.encoding.manifests.hls.media.audio.create(
                manifest_id=hls_manifest.id,
                audio_media_info=AudioMediaInfo(
                    name='AAC',
                    group_id='audio',
                    language='en',
                    segment_path=segment_path,
                    encoding_id=encoding_id,
                    stream_id=stream.id,
                    muxing_id=muxing.id,
                    uri='aac_audio_{}.m3u8'.format(audio_codec.bitrate)))

    return hls_manifest


def _execute_dash_manifest_generation(dash_manifest):
    bitmovin_api.encoding.manifests.dash.start(manifest_id=dash_manifest.id)

    task = _wait_for_dash_manifest_to_finish(manifest_id=dash_manifest.id)

    while task.status is not Status.FINISHED and task.status is not Status.ERROR:
        task = _wait_for_dash_manifest_to_finish(manifest_id=dash_manifest.id)
    if task.status is Status.ERROR:
        _log_task_errors(task=task)
        raise Exception("DASH Manifest Creation failed")

    print("DASH Manifest Creation finished successfully")


def _execute_hls_manifest_generation(hls_manifest):
    bitmovin_api.encoding.manifests.hls.start(manifest_id=hls_manifest.id)

    task = _wait_for_hls_manifest_to_finish(manifest_id=hls_manifest.id)

    while task.status is not Status.FINISHED and task.status is not Status.ERROR:
        task = _wait_for_hls_manifest_to_finish(manifest_id=hls_manifest.id)
    if task.status is Status.ERROR:
        _log_task_errors(task=task)
        raise Exception("HLS Manifest Creation failed")

    print("HLS Manifest Creation finished successfully")


def _wait_for_enoding_to_finish(encoding_id):
    time.sleep(5)
    task = bitmovin_api.encoding.encodings.status(encoding_id=encoding_id)
    print("Encoding status is {} (progress: {} %)".format(task.status, task.progress))
    return task


def _wait_for_dash_manifest_to_finish(manifest_id):
    time.sleep(5)
    task = bitmovin_api.encoding.manifests.dash.status(manifest_id=manifest_id)
    print("DASH manifest status is {} (progress: {} %)".format(task.status, task.progress))
    return task


def _wait_for_hls_manifest_to_finish(manifest_id):
    time.sleep(5)
    task = bitmovin_api.encoding.manifests.hls.status(manifest_id=manifest_id)
    print("HLS manifest status is {} (progress: {} %)".format(task.status, task.progress))
    return task


def _remove_output_base_path(text):
    if text.startswith(OUTPUT_BASE_PATH):
        return text[len(OUTPUT_BASE_PATH):]
    return text


def _log_task_errors(task):
    if task is None:
        return

    filtered = filter(lambda msg: msg.type is MessageType.ERROR, task.messages)

    for message in filtered:
        print(message.text)


if __name__ == '__main__':
    main()
