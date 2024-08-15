import os
import shutil
import torch
from time import strftime
from Libraries.SadTalker.src.utils.preprocess import CropAndExtract
from Libraries.SadTalker.src.test_audio2coeff import Audio2Coeff  
from Libraries.SadTalker.src.facerender.animate import AnimateFromCoeff
from Libraries.SadTalker.src.generate_batch import get_data
from Libraries.SadTalker.src.generate_facerender_batch import get_facerender_data
from Libraries.SadTalker.src.utils.init_path import init_path

class Args:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

class videoGen():
    def __init__(self):
        pass

    def generate_video(self,
        driven_audio='./Libraries/SadTalker/examples/driven_audio/bus_chinese.wav',
        source_image='./Libraries/SadTalker/examples/source_image/teacher.jpeg',
        pdfName = '',
        ref_eyeblink=None,
        ref_pose=None,
        checkpoint_dir='./Libraries/SadTalker/checkpoints',
        result_dir='./static/results/',
        pose_style=0,
        batch_size=1,
        size=256,
        expression_scale=1.0,
        input_yaw=None,
        input_pitch=None,
        input_roll=None,
        enhancer=None,
        background_enhancer=None,
        cpu=False,
        face3dvis=False,
        still=True,
        preprocess='crop',
        verbose=False,
        old_version=False,
        net_recon='resnet50',
        init_path_param=None,
        use_last_fc=False,
        bfm_folder='./Libraries/SadTalker/checkpoints/BFM_Fitting/',
        bfm_model='BFM_model_front.mat',
        focal=1015.0,
        center=112.0,
        camera_d=10.0,
        z_near=5.0,
        z_far=15.0
    ):
        device = "cuda" if torch.cuda.is_available() and not cpu else "cpu"
        args = Args(
            driven_audio=driven_audio,
            source_image=source_image,
            ref_eyeblink=ref_eyeblink,
            ref_pose=ref_pose,
            checkpoint_dir=checkpoint_dir,
            result_dir=result_dir,
            pose_style=pose_style,
            batch_size=batch_size,
            size=size,
            expression_scale=expression_scale,
            input_yaw=input_yaw,
            input_pitch=input_pitch,
            input_roll=input_roll,
            enhancer=enhancer,
            background_enhancer=background_enhancer,
            cpu=cpu,
            face3dvis=face3dvis,
            still=still,
            preprocess=preprocess,
            verbose=verbose,
            old_version=old_version,
            net_recon=net_recon,
            init_path_param=init_path_param,
            use_last_fc=use_last_fc,
            bfm_folder=bfm_folder,
            bfm_model=bfm_model,
            focal=focal,
            center=center,
            camera_d=camera_d,
            z_near=z_near,
            z_far=z_far,
            device=device
        )
        save_dir = os.path.join(result_dir, strftime("%Y_%m_%d_%H.%M.%S"))
        os.makedirs(save_dir, exist_ok=True)

        current_root_path = "./Libraries/SadTalker"
        sadtalker_paths = init_path(checkpoint_dir, os.path.join(current_root_path, 'src/config'), size, old_version, preprocess)

        preprocess_model = CropAndExtract(sadtalker_paths, device)
        audio_to_coeff = Audio2Coeff(sadtalker_paths, device)
        animate_from_coeff = AnimateFromCoeff(sadtalker_paths, device)

        first_frame_dir = os.path.join(save_dir, 'first_frame_dir')
        os.makedirs(first_frame_dir, exist_ok=True)
        print('3DMM Extraction for source image')
        first_coeff_path, crop_pic_path, crop_info = preprocess_model.generate(source_image, first_frame_dir, preprocess, source_image_flag=True, pic_size=size)
        
        if first_coeff_path is None:
            print("Can't get the coeffs of the input")
            return

        ref_eyeblink_coeff_path = None
        if ref_eyeblink:
            ref_eyeblink_videoname = os.path.splitext(os.path.split(ref_eyeblink)[-1])[0]
            ref_eyeblink_frame_dir = os.path.join(save_dir, ref_eyeblink_videoname)
            os.makedirs(ref_eyeblink_frame_dir, exist_ok=True)
            print('3DMM Extraction for the reference video providing eye blinking')
            ref_eyeblink_coeff_path, _, _ = preprocess_model.generate(ref_eyeblink, ref_eyeblink_frame_dir, preprocess, source_image_flag=False)

        ref_pose_coeff_path = None
        if ref_pose:
            if ref_pose == ref_eyeblink:
                ref_pose_coeff_path = ref_eyeblink_coeff_path
            else:
                ref_pose_videoname = os.path.splitext(os.path.split(ref_pose)[-1])[0]
                ref_pose_frame_dir = os.path.join(save_dir, ref_pose_videoname)
                os.makedirs(ref_pose_frame_dir, exist_ok=True)
                print('3DMM Extraction for the reference video providing pose')
                ref_pose_coeff_path, _, _ = preprocess_model.generate(ref_pose, ref_pose_frame_dir, preprocess, source_image_flag=False)

        batch = get_data(first_coeff_path, driven_audio, device, ref_eyeblink_coeff_path, still=still)
        coeff_path = audio_to_coeff.generate(batch, save_dir, pose_style, ref_pose_coeff_path)

        if face3dvis:
            from src.face3d.visualize import gen_composed_video
            gen_composed_video(args, device, first_coeff_path, coeff_path, driven_audio, os.path.join(save_dir, '3dface.mp4'))
        
        data = get_facerender_data(coeff_path, crop_pic_path, first_coeff_path, driven_audio, 
                                batch_size, input_yaw, input_pitch, input_roll,
                                expression_scale=expression_scale, still_mode=still, preprocess=preprocess, size=size)
        
        result = animate_from_coeff.generate(data, save_dir, source_image, crop_info, 
                                            enhancer=enhancer, background_enhancer=background_enhancer, preprocess=preprocess, img_size=size)
        finalPath = os.path.join(result_dir,pdfName+".mp4")
        shutil.move(result,finalPath)
        print('The generated video is named:', finalPath)

        if not verbose:
            shutil.rmtree(save_dir)
        return save_dir+'.mp4'

