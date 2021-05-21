import torch


def trimodal_loss(models, sample, batch_size, device, loss, labels, data_dict, config):
    # Encode the sample
    sample["rgb"] = sample["rgb"].view(-1, 3, 84, 84)
    rgb_z = models["trimodal"]["viz_enc"](sample["rgb"].float().to(device))

    rgb_traj_z = models["trimodal"]["viz_traj_enc"](rgb_z, batch_size)
    initial_rgb_z = models["trimodal"]["viz_enc"](sample["initial_rgb"].float().to(device)).view(batch_size, 50)
    spectrogram_z = models["trimodal"]["audio_enc"](sample["spectrogram"].float().to(device))
    actions_z = models["trimodal"]["action_enc"](initial_rgb_z, sample["actions"].float().to(device))

    # 3 way loss
    rgb_audio_probs = models["trimodal"]["comp_enc"](rgb_traj_z, spectrogram_z)
    rgb_audio_loss = loss[0](rgb_audio_probs, labels)
    correct_rgb_audio = int(torch.sum(torch.argmax(rgb_audio_probs, axis=1) == labels).detach().cpu().numpy())

    rgb_actions_probs = models["trimodal"]["comp_enc"](rgb_traj_z, actions_z)
    rgb_action_loss = loss[1](rgb_actions_probs, labels)
    correct_rgb_actions = int(torch.sum(torch.argmax(rgb_actions_probs, axis=1) == labels).detach().cpu().numpy())

    audio_actions_probs = models["trimodal"]["comp_enc"](spectrogram_z, actions_z)
    audio_action_loss = loss[2](audio_actions_probs, labels)
    correct_audio_actions = int(torch.sum(torch.argmax(audio_actions_probs, axis=1) == labels).detach().cpu().numpy())

    total_loss = rgb_audio_loss + rgb_action_loss + audio_action_loss
    data_dict["epoch_losses"][0].append(rgb_audio_loss.item())
    data_dict["epoch_losses"][1].append(rgb_action_loss.item())
    data_dict["epoch_losses"][2].append(audio_action_loss.item())
    data_dict["epoch_losses"][3].append(total_loss.item())
    data_dict["epoch_num_cor"][0] += correct_rgb_audio
    data_dict["epoch_num_cor"][1] += correct_rgb_actions
    data_dict["epoch_num_cor"][2] += correct_audio_actions
    data_dict["batches"] += 1
    return total_loss


def bimodal_loss(models, sample, batch_size, device, loss, labels, data_dict, config):
    if config["rgb_mode"] == "rgb":
        sample["rgb"] = sample["rgb"].view(-1, 3, 84, 84).float().to(device)
    elif config["rgb_mode"] == "optical_flow":
        sample["optical_flow"] = sample["optical_flow"].view(-1, 3, 84, 84).float().to(device)
    sample["spectrogram"] = sample["spectrogram"].float().to(device)
    sample["initial_rgb"] = sample["initial_rgb"].float().to(device)
    sample["actions"] = sample["actions"].float().to(device)

    # RGB AUDIO
    if config["rgb_mode"] == "rgb":
        rgb_z = models["rgb_audio"]["viz_enc"](sample["rgb"])
    elif config["rgb_mode"] == "optical_flow":
        rgb_z = models["rgb_audio"]["flow_enc"](sample["optical_flow"])
    rgb_traj_z = models["rgb_audio"]["viz_traj_enc"](rgb_z, batch_size)
    spectrogram_z = models["rgb_audio"]["audio_enc"](sample["spectrogram"])
    rgb_audio_probs = models["rgb_audio"]["comp_enc"](rgb_traj_z, spectrogram_z)
    rgb_audio_loss = loss[0](rgb_audio_probs, labels)
    correct_rgb_audio = int(torch.sum(torch.argmax(rgb_audio_probs, axis=1) == labels).detach().cpu().numpy())

    # RGB ACTIONS
    initial_rgb_z = models["rgb_actions"]["viz_enc"](sample["initial_rgb"]).view(batch_size, 50)
    if config["rgb_mode"] == "rgb":
        rgb_z = models["rgb_actions"]["viz_enc"](sample["rgb"])
    elif config["rgb_mode"] == "optical_flow":
        rgb_z = models["rgb_actions"]["flow_enc"](sample["optical_flow"])
    rgb_traj_z = models["rgb_actions"]["viz_traj_enc"](rgb_z, batch_size)
    actions_z = models["rgb_actions"]["action_enc"](initial_rgb_z, sample["actions"])
    rgb_actions_probs = models["rgb_actions"]["comp_enc"](rgb_traj_z, actions_z)
    rgb_action_loss = loss[1](rgb_actions_probs, labels)
    correct_rgb_actions = int(torch.sum(torch.argmax(rgb_actions_probs, axis=1) == labels).detach().cpu().numpy())

    # AUDIO ACTIONS
    initial_rgb_z = models["audio_actions"]["viz_enc"](sample["initial_rgb"]).view(batch_size, 50)
    actions_z = models["audio_actions"]["action_enc"](initial_rgb_z, sample["actions"])
    spectrogram_z = models["audio_actions"]["audio_enc"](sample["spectrogram"])
    audio_actions_probs = models["audio_actions"]["comp_enc"](spectrogram_z, actions_z)
    audio_action_loss = loss[2](audio_actions_probs, labels)
    correct_audio_actions = int(torch.sum(torch.argmax(audio_actions_probs, axis=1) == labels).detach().cpu().numpy())

    total_loss = rgb_audio_loss + rgb_action_loss + audio_action_loss
    data_dict["epoch_losses"][0].append(rgb_audio_loss.item())
    data_dict["epoch_losses"][1].append(rgb_action_loss.item())
    data_dict["epoch_losses"][2].append(audio_action_loss.item())
    data_dict["epoch_losses"][3].append(total_loss.item())
    data_dict["epoch_num_cor"][0] += correct_rgb_audio
    data_dict["epoch_num_cor"][1] += correct_rgb_actions
    data_dict["epoch_num_cor"][2] += correct_audio_actions
    data_dict["batches"] += 1
    return total_loss