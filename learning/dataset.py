import numpy as np
import os
import cv2
import json
import soundfile as sf
import matplotlib.pyplot as plt
import torch
from torch.utils.data import Dataset, TensorDataset
from torch.utils.data import DataLoader
from torch.utils.data.dataset import random_split
import librosa


class HWDataset:
    def __init__(self, config):
        self.config = config
        self.data = {"paths": dict(), "length": -1, "means": dict(), "stds": dict()}
        self.setup_dataset()

    def __len__(self):
        return self.config["max_samples"]

    def setup_dataset(self):
        """
        Look at the dataset path and determine dataset size. Normalize data.
        :return: None
        """
        dataset_path = f"{self.config['dataset_path']}/{self.config['dataset_name']}"
        files = os.listdir(dataset_path)
        if self.config["max_samples"] == "max":
            self.config["max_samples"] = len(files)
        self.data["length"] = min(len(files), self.config["max_samples"])
        for sample_num in range(self.data["length"]):
            self.data["paths"][sample_num] = f"{dataset_path}/{sample_num}"

    def normalize_data(self):
        """
        Normalize the dataset over the first N samples.
        :return: None
        """
        normal_num = min(self.data["length"], 50)
        spectros = np.zeros([normal_num, 128, 94])
        for idx in range(normal_num):
            sample = self.get_sample(idx)
            spectros[idx] = sample["spectrogram"]
        self.data["means"]["spectrogram"] = np.mean(spectros)
        self.data["stds"]["spectrogram"] = np.std(spectros)

    def get_normalized_sample(self, idx):
        sample = self.get_sample(idx)
        sample["rgb"] = sample["rgb"].copy() / 255.
        sample["spectrogram"] = \
            (sample["spectrogram"] - self.data["means"]["spectrogram"]) / self.data["stds"]["spectrogram"]
        return sample

    def get_sample(self, idx, resize_rgb=True):
        sample = {"rgb": self.get_rgb(idx, resize_rgb), "audio": self.get_audio(idx),
                  "angle": self.get_action_angle(idx),
                  "speed": self.get_action_speed(idx),
                  }
        sample["spectrogram"] = self.calc_spectrogram(sample["audio"])
        return sample

    def get_action_angle(self, idx):
        with open(f'{self.data["paths"][idx]}/data.json') as json_file:
            return eval(json.load(json_file))["angle_traj"]

    def get_action_speed(self, idx):
        with open(f'{self.data["paths"][idx]}/data.json') as json_file:
            return eval(json.load(json_file))["speed_traj"]

    def get_rgb(self, idx, resize_rgb):
        if not resize_rgb:
            return np.array([plt.imread(f'{self.data["paths"][idx]}/rgb{num}.jpg') for num in range(13)])
        else:
            return np.array([
                cv2.resize(plt.imread(f'{self.data["paths"][idx]}/rgb{num}.jpg'), (100, 100)) for num in range(13)])

    def get_audio(self, idx):
        return sf.read(f'{self.data["paths"][idx]}/audio.wav', dtype='float32')[0][:96000]

    @staticmethod
    def calc_spectrogram(audio):
        S = librosa.feature.melspectrogram(
            y=audio, sr=48000, S=None, n_fft=2048, hop_length=1024, power=2.0)
        return np.log10(S + 1e-10)


class TorchDataset(Dataset, HWDataset):
    def __init__(self, config):
        super().__init__(config)
        self.config = config
        self.normalize_data()

    def get_trajectory_crop_idx(self):
        i0_rgb, i1_rgb = self.config["rgb_offset"], 13
        i0_audio = np.random.randint(0, 5)
        i1_audio = 94 - (4-i0_audio)
        return [i0_rgb, i1_rgb, i0_audio, i1_audio]

    @staticmethod
    def get_random_crop_idx():
        # Find top left pixel. Output for 100x100 cropped to 84x84.
        top_left_x, top_left_y = np.random.randint(0, 16), np.random.randint(0, 16)
        return top_left_x, 100 - (16 - top_left_x), top_left_y, 100 - (16 - top_left_y)

    def __getitem__(self, idx):
        norm_sample = self.get_normalized_sample(idx)
        t_idx = self.get_trajectory_crop_idx()
        rgb_data = norm_sample["rgb"][t_idx[0]:t_idx[1]]
        rgb_data = rgb_data.transpose([0, 3, 1, 2])
        r_idx = self.get_random_crop_idx()
        rgb_data = rgb_data[:, :, r_idx[0]:r_idx[1], r_idx[2]:r_idx[3]]
        actions = np.concatenate([np.array(norm_sample["angle"]) / 360., np.array(norm_sample["speed"]) / 255.])
        spectrogram_data = norm_sample["spectrogram"].reshape([1, 128, 94])[:, :, t_idx[2]:t_idx[3]]
        # initial_rgb = norm_sample["rgb"][0].transpose(2, 0, 1)[:, r_idx[0]:r_idx[1], r_idx[2]:r_idx[3]]
        return {"rgb": rgb_data, "spectrogram": spectrogram_data, "idx": idx, "actions": actions}


class TorchDataLoader:
    def __init__(self, config):
        self.full_dataset = TorchDataset(config)
        num_train = int(config["train_ratio"] * len(self.full_dataset))
        self.train_dataset, self.val_dataset = random_split(self.full_dataset,
                                                            [num_train, len(self.full_dataset) - num_train],
                                                            generator=torch.Generator().manual_seed(42))
        self.full_dataloader = DataLoader(self.full_dataset, batch_size=config["batch_size_train"], shuffle=True)
        self.train_dataloader = DataLoader(self.train_dataset, batch_size=config["batch_size_train"], shuffle=True)
        self.val_dataloader = DataLoader(self.val_dataset, batch_size=config["batch_size_valid"], shuffle=True)
        self.dataloaders = (self.full_dataloader, self.train_dataloader, self.val_dataloader)
