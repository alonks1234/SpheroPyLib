from contrastive_models import ModelWrapper
import torch
from dataset import TorchDataset, TorchDataLoader
import numpy as np
from SpheroLib.config import sphero_config
# from SpheroLib.sphero_library import SpheroLibrary
from SpheroLib.fake_sphero_library import SpheroLibrary
import os
from pathlib import Path
import cv2
import json
import time
from scipy.io.wavfile import write
from matplotlib import pyplot as plt


def cem_optimize(initial_guess, source_encoding, initial_rgb_encoding, model, device):
    p_num, top_p = 500, 15
    source_encoding = torch.FloatTensor(source_encoding).to(device)
    mu, sigma = torch.FloatTensor(initial_guess), torch.ones(8) * .2
    rgb_init_torch = torch.FloatTensor(initial_rgb_encoding).to(device).repeat(p_num, 1)
    for i in range(3):
        particles = torch.clip(torch.vstack([torch.normal(mu, sigma) for part_elt in range(p_num)]), 0, 1).to(device)
        action_encodings = model.models["trimodal"]["action_enc"](rgb_init_torch, particles)
        error = torch.norm(action_encodings - source_encoding, dim=1)
        top_particles = particles[torch.topk(-error, top_p).indices]
        mu, sigma = torch.mean(top_particles, dim=0), torch.std(top_particles, dim=0)
    heading_traj = (mu[:4] * 360.).detach().cpu().numpy().astype('int')
    speed_traj = (mu[4:] * 255.).detach().cpu().numpy().astype('int')
    return heading_traj, speed_traj


def run_cem_data_collection(config, save_model_path):
    import multiprocessing as mp
    mp.set_start_method("spawn")

    config["num_img_traj"] = 13 - config['rgb_offset']
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    model = ModelWrapper(config)
    model.to(device)
    model.load_state_dict(torch.load(save_model_path, map_location=device))
    dataloader = TorchDataLoader(config)
    total_samples = len(dataloader.full_dataset)
    num_samples = 10
    pointer = 0
    # Setup the dataset folders
    original_dataset = f"{config['dataset_path']}/{config['dataset_name']}"
    cem_dataset = f"{original_dataset}_cem"
    metadata_folder = f"{cem_dataset}/metadata"
    initial_encoding_save_path = f"{metadata_folder}/initial_encodings.npy"
    audio_encoding_save_path = f"{metadata_folder}/audio_encodings.npy"
    matches_path = f"{metadata_folder}/matches.json"
    dir_path = Path(f"{cem_dataset}")
    if dir_path.exists() and dir_path.is_dir():
        start_num = len(os.listdir(cem_dataset)) - 1 + len(os.listdir(original_dataset))
        initial_encodings = np.load(initial_encoding_save_path)
        audio_encodings = np.load(audio_encoding_save_path)
        with open(matches_path) as json_file:
            matches_dict = eval(json.load(json_file))

    else:
        initial_encodings = np.zeros([total_samples, 50])
        audio_encodings = np.zeros([total_samples, 50])
        start_num = len(os.listdir(original_dataset))
        os.mkdir(cem_dataset)
        os.mkdir(metadata_folder)

        # Iterate through the dataset, saving the model encoding of the first image in each sample
        for batch in dataloader.full_dataloader:
            rgb_initial = batch['rgb'][:, 0].float().to(device)
            spectrogram = batch['spectrogram'].float().to(device)
            num_batch = spectrogram.size()[0]
            with torch.no_grad():
                audio_encoding = model.models['trimodal']['audio_enc'](spectrogram).detach().cpu().numpy()
                audio_encodings[pointer:pointer+num_batch] = audio_encoding
                initial_encoding = model.models['trimodal']['viz_enc'](rgb_initial).detach().cpu().numpy()
                initial_encodings[pointer:pointer+num_batch] = initial_encoding
                pointer += num_batch
        np.save(initial_encoding_save_path, initial_encodings)
        np.save(audio_encoding_save_path, initial_encodings)
        matches_dict = {}
        with open(matches_path, 'w') as pkl_file:
            json.dump(repr(matches_dict), pkl_file)
    """ 
    Generate a new dataset by:
        * Capturing the current image.
        * Finding the nearest neighbor in initial_encodings.
        * Taking the sound encoding of the nearest neighbor.
        * Optimizing the actions of the current model to match this encoding.
        * Rolling out the actions.
        * Saving the sample, along with the target sample.
    """
    sphero_lib = SpheroLibrary(sphero_config)
    output = sphero_lib.get_sphero_states()
    for sample in range(start_num, start_num + num_samples):
        print(f"\rGathering Sample {sample}/{num_samples}", end=' ')
        sample_path = f"{cem_dataset}/{sample}"
        [initial_state, _] = sphero_lib.get_sphero_states()
        initial_image = cv2.resize(initial_state["rgb"][-1][:, 60:240], (100, 100))
        initial_image_refactored = (initial_image[:, :, ::-1] / 255.).transpose(2, 1, 0)[:, 8:92, 8:92]
        initial_image_tensor = torch.unsqueeze(torch.FloatTensor(initial_image_refactored).to(device), 0)
        initial_image_encoding = model.models['trimodal']['viz_enc'](initial_image_tensor).detach().cpu().numpy()
        distances = np.linalg.norm(initial_encodings - initial_image_encoding, axis=1)
        closest_idx = np.argmin(distances)
        source_audio_encoding = audio_encodings[closest_idx]
        closest_sample = dataloader.full_dataset.get_sample(closest_idx, resize_rgb=False)
        source_actions = np.concatenate([np.array(closest_sample["angle"])/360.,
                                         np.array(closest_sample["speed"])/255.])
        heading_trajectory, speed_trajectory = cem_optimize(source_actions, source_audio_encoding,
                                                            initial_image_encoding, model, device)

        for elt in range(4):
            action_start = time.time()
            sphero_lib.set_sphero_action(0, heading_trajectory[elt], speed_trajectory[elt])
            time.sleep(max([.5 - (time.time() - action_start), 0]))
        [state, _] = sphero_lib.get_sphero_states()
        sphero_lib.set_sphero_action(0, heading_trajectory[-1], 0)
        time.sleep(1)
        # Viz the trajectory
        current_img_traj = np.concatenate(np.vstack([np.array([initial_state["rgb"][-1][:, 60:240]]), state["rgb"][:, :, 60:240]]), axis=1)
        closest_img_traj = np.concatenate(closest_sample["rgb"], axis=1)
        combined_image = np.vstack([current_img_traj, closest_img_traj])
        plt.imshow(combined_image)
        plt.pause(1)

        # Save the new data
        matches_dict[sample] = closest_idx
        with open(matches_path, 'w') as pkl_file:
            json.dump(repr(matches_dict), pkl_file)
        os.mkdir(sample_path)
        cv2.imwrite(f"{sample_path}/rgb0.jpg", initial_state["rgb"][-1][:, 60:240])
        cv2.imwrite(f"{sample_path}/depth0.jpg", initial_state["depth"][-1][:, 70:310] / 64)
        write(f"{sample_path}/audio.wav", sphero_config["AUDIO_BYTES_PER_SECOND"], state["audio"].flatten())
        [cv2.imwrite(f"{sample_path}/rgb{rgb_elt + 1}.jpg", rgb[:, 60:240]) for rgb_elt, rgb in enumerate(state["rgb"])]
        [cv2.imwrite(f"{sample_path}/depth{d_elt + 1}.jpg", depth[:, 70:310] / 64) for d_elt, depth in
         enumerate(state["depth"])]
        sphero_data = {sensor: list(state["spheros"][0][:, sensor_elt]) for sensor_elt, sensor in
                       enumerate(sphero_config["SPHERO_OUTPUT_VARIABLES"])}
        sphero_data["angle_traj"] = list(heading_trajectory)
        sphero_data["speed_traj"] = list(speed_trajectory)
        with open(f"{sample_path}/data.json", 'w') as pkl_file:
            json.dump(repr(sphero_data), pkl_file)
        calm = False
        calm_start = time.time()
        while not calm:
            [state, timestamps] = sphero_lib.get_sphero_states()
            current_state = state["spheros"][0][0]
            speed = (current_state[3] ** 2 + current_state[4] ** 2) ** .5
            rotation = (current_state[5] ** 2 + current_state[6] ** 2 + current_state[7] ** 2) ** .5
            if (rotation < 15 and speed < 10) or time.time() - calm_start > 3:
                calm = True
        random_heading = np.random.randint(0, 360)
        sphero_lib.set_sphero_action(0, random_heading, 0)
        time.sleep(1)


if __name__ == "__main__":
    config = {
        "dataset_path": "/home/alon/datasets/", "dataset_name": "hw_dataset_craigie", "train_ratio": .8,
        "max_samples": 30,
        "batch_size_train": 64, "batch_size_valid": 64, "rgb_offset": 4,
        "save": True,
        "cnn_backbone": "resnet", "pretrained": False, "trainable": True,
        "architecture": "trimodal", "adam": True, "epochs": 10,
    }
    run_cem_data_collection(config, "trimodal_models/wrapper_model.pt")
