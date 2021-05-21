from dataset import TorchDataset, TorchDataLoader
from torch.utils.tensorboard import SummaryWriter
import torch
from contrastive_models import ModelWrapper
from losses import bimodal_loss, trimodal_loss
import os
import numpy as np
import shutil
import matplotlib.pyplot as plt


def visualize_data(train_dict, val_dict, writer, epoch):
    fig = plt.figure(figsize=(20, 20))
    gs = fig.add_gridspec(2, 1)
    ax_loss = fig.add_subplot(gs[0])
    ax_acc = fig.add_subplot(gs[1])
    xs = np.arange(epoch + 1)
    for mode, (data_dict, v_tag) in {"Train": (train_dict, '-'), "Val": (val_dict, 'o')}.items():
        losses = np.array(data_dict["losses"])
        accuracies = np.array(data_dict["accuracies"])
        for elt, (c, compare_name) in enumerate([("r", "rgb_audio"), ("g", "rgb_action"),
                                                 ("b", "action_audio"), ("k", "total")]):
            ax_loss.plot(xs, losses[:, elt], f'{c}{v_tag}', label=f"{mode} Loss/{compare_name}")
            if elt != 3:
                ax_acc.plot(xs, accuracies[:, elt], f'{c}{v_tag}', label=f"{mode} Acc/{compare_name}")
    ax_acc.legend()
    ax_loss.legend()
    writer.add_figure("Training Summary", fig, global_step=epoch, close=True)


def train_representations(config):
    """
    Create torch dataset/dataloader objects. Initialize models, optimizer, losses, labels.
    """
    # writer_comment = f"-b:{config['batch_size_train']}-adam:{config['adam']}lr:{config['lr']}-g:{config['gamma']}-m:{config['milestones']}-s:{config['max_samples']}-arch:{config['architecture']}-backbone:{config['cnn_backbone']}-rmode:{config['rgb_mode']}-roffs:{config['rgb_offset']}-tag:{config['tag']}"
    config["num_img_traj"] = 13 - config['rgb_offset']
    writer = SummaryWriter(comment="")
    dataloader = TorchDataLoader(config)
    full_dataloader, train_dataloader, val_dataloader = dataloader.dataloaders
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    model_wrapper = ModelWrapper(config)
    model_wrapper.to(device)
    ce_loss = torch.nn.CrossEntropyLoss(), torch.nn.CrossEntropyLoss(), torch.nn.CrossEntropyLoss()
    mse_loss = torch.nn.MSELoss(reduction='none')
    labels_train = torch.arange(config["batch_size_train"]).to(device)
    labels_valid = torch.arange(config["batch_size_valid"]).to(device)
    """
    Run training and validation iterations.
    """
    train_data = {"losses": [], "accuracies": [], "batch_size": config["batch_size_train"]}
    val_data = {"losses": [], "accuracies": [], "batch_size": config["batch_size_valid"]}
    for epoch in range(config["epochs"]):
        train_data["batches"], val_data["batches"] = 0, 0
        train_data["epoch_num_cor"], val_data["epoch_num_cor"] = [0, 0, 0], [0, 0, 0]
        train_data["epoch_losses"], val_data["epoch_losses"] = ([], [], [], []), ([], [], [], [])

        for key in model_wrapper.models.keys():
            [model.train() for model in model_wrapper.models[key].values()]

        for sample_elt, sample in enumerate(train_dataloader):
            if len(sample["rgb"]) < config["batch_size_train"]:
                continue
            if config["architecture"] == "trimodal":
                batch_loss = trimodal_loss(model_wrapper.models, sample, config["batch_size_train"], device, ce_loss,
                                           labels_train, train_data, config)

            elif config["architecture"] == "bimodal":
                batch_loss = bimodal_loss(model_wrapper.models, sample, config["batch_size_train"], device, ce_loss,
                                          labels_train, train_data, config)
            batch_loss.backward()
            for key, optimizer in model_wrapper.optimizers.items():
                optimizer.step()
                optimizer.zero_grad()

        with torch.no_grad():
            for key in model_wrapper.models.keys():
                [model.eval() for model in model_wrapper.models[key].values()]

            for sample_elt, sample in enumerate(val_dataloader):
                if len(sample["rgb"]) < config["batch_size_valid"]:
                    continue

                if config["architecture"] == "trimodal":
                    batch_loss = trimodal_loss(model_wrapper.models, sample, config["batch_size_valid"], device,
                                               ce_loss,
                                               labels_valid, val_data, config)
                elif config["architecture"] == "bimodal":
                    batch_loss = bimodal_loss(model_wrapper.models, sample, config["batch_size_valid"], device, ce_loss,
                                              labels_valid, val_data, config)

        for mode, data_dict in {"Train": train_data, "Val": val_data}.items():
            data_dict["acc_epoch"] = np.array(data_dict["epoch_num_cor"]) / (
                    data_dict["batch_size"] * data_dict["batches"])
            data_dict["avg_loss_epoch"] = np.mean(data_dict["epoch_losses"], axis=1)
            data_dict["losses"].append(data_dict["avg_loss_epoch"])
            data_dict["accuracies"].append(data_dict["acc_epoch"])
            writer.add_scalar(f'Loss/{mode} rgb audio', data_dict["avg_loss_epoch"][0], epoch)
            writer.add_scalar(f'Loss/{mode} rgb actions', data_dict["avg_loss_epoch"][1], epoch)
            writer.add_scalar(f'Loss/{mode} audio actions', data_dict["avg_loss_epoch"][2], epoch)
            writer.add_scalar(f'Loss/{mode} total', data_dict["avg_loss_epoch"][3], epoch)
            writer.add_scalar(f'Accuracy/{mode} rgb audio', data_dict["acc_epoch"][0], epoch)
            writer.add_scalar(f'Accuracy/{mode} rgb actions', data_dict["acc_epoch"][1], epoch)
            writer.add_scalar(f'Accuracy/{mode} audio actions', data_dict["acc_epoch"][2], epoch)
        visualize_data(train_data, val_data, writer, epoch)
        print(train_data["losses"][-1], val_data["losses"][-1], train_data["acc_epoch"], val_data["acc_epoch"])

        if config["save"]:
            model_save_dir = f"{config['architecture']}_models"
            if os.path.exists(model_save_dir):
                shutil.rmtree(model_save_dir)
            os.mkdir(model_save_dir)
            torch.save(model_wrapper.state_dict(), f"{model_save_dir}/wrapper_model.pt")

        [scheduler.step() for scheduler in model_wrapper.schedulers]


if __name__ == "__main__":
        config = {
                "dataset_path": "hw_dataset_craigie", "train_ratio": .8, "max_samples": "max",
                "batch_size_train": 64, "batch_size_valid": 64, "rgb_offset": 4,
                "save": True,
                "cnn_backbone": "resnet", "pretrained": False, "trainable": True,
                "architecture": "trimodal", "adam": True, "epochs": 10,
        }
        train_representations(config)

