import pytest
from types import SimpleNamespace
from providers.pose.canonical import map_pose_frame, JOINT_INDICES


def test_joint_indices():
    assert JOINT_INDICES["left_shoulder"] == 11
    assert JOINT_INDICES["right_ankle"] == 28


def test_valid_mapping():
    image_lm = [SimpleNamespace(x=0.1, y=0.2, visibility=0.9, presence=0.8) for _ in range(33)]
    world_lm = [SimpleNamespace(x=1.0, y=2.0, z=3.0) for _ in range(33)]
    frame = map_pose_frame(image_lm, world_lm, frame_index=5, timestamp_s=1.5)
    joint = frame.joints["left_shoulder"]
    assert joint.xy == (0.1, 0.2)
    assert joint.xyz == (1.0, -2.0, -3.0)
    assert joint.native_quality == 0.8
    assert joint.valid is True


def test_low_quality_invalid():
    image_lm = [SimpleNamespace(x=0.1, y=0.2, visibility=0.5, presence=0.4) for _ in range(33)]
    world_lm = [SimpleNamespace(x=1.0, y=2.0, z=3.0) for _ in range(33)]
    frame = map_pose_frame(image_lm, world_lm, frame_index=0, timestamp_s=0.0, visibility_threshold=0.6)
    joint = frame.joints["left_wrist"]
    assert joint.xy == (0.1, 0.2)
    assert joint.xyz == (1.0, -2.0, -3.0)
    assert joint.valid is False


def test_missing_world_retains_xy_invalid():
    image_lm = [SimpleNamespace(x=0.1, y=0.2, visibility=0.9, presence=0.8) for _ in range(33)]
    frame = map_pose_frame(image_lm, [], frame_index=0, timestamp_s=0.0)
    joint = frame.joints["left_hip"]
    assert joint.xy == (0.1, 0.2)
    assert joint.xyz is None
    assert joint.valid is False


def test_nonfinite_coordinates_none():
    image_lm = [SimpleNamespace(x=0.1, y=float('inf'), visibility=0.9, presence=0.8) for _ in range(33)]
    world_lm = [SimpleNamespace(x=1.0, y=2.0, z=float('nan')) for _ in range(33)]
    frame = map_pose_frame(image_lm, world_lm, frame_index=0, timestamp_s=0.0)
    joint = frame.joints["left_knee"]
    assert joint.xy is None
    assert joint.xyz is None
    assert joint.valid is False


def test_derived_joints_only_when_both_valid():
    image_lm = [SimpleNamespace(x=0.1, y=0.2, visibility=0.9, presence=0.8) for _ in range(33)]
    world_lm = [SimpleNamespace(x=1.0, y=2.0, z=3.0) for _ in range(33)]
    image_lm[JOINT_INDICES["left_hip"]].x = 0.3
    frame = map_pose_frame(image_lm, world_lm, frame_index=0, timestamp_s=0.0)
    pelvis = frame.joints["pelvis"]
    assert pelvis.xy == (0.2, 0.2)
    assert "derived_paired_midpoint" in pelvis.quality_method


def test_wrong_lengths_raise():
    image_lm = [SimpleNamespace(x=0.1, y=0.2, visibility=0.9, presence=0.8) for _ in range(10)]
    world_lm = [SimpleNamespace(x=1.0, y=2.0, z=3.0) for _ in range(33)]
    with pytest.raises(ValueError, match="length 0 or 33"):
        map_pose_frame(image_lm, world_lm, frame_index=0, timestamp_s=0.0)
    with pytest.raises(ValueError, match="length 0 or 33"):
        map_pose_frame(world_lm, image_lm, frame_index=0, timestamp_s=0.0)


def test_invalid_visibility_threshold():
    image_lm = [SimpleNamespace(x=0.1, y=0.2, visibility=0.9, presence=0.8) for _ in range(33)]
    world_lm = [SimpleNamespace(x=1.0, y=2.0, z=3.0) for _ in range(33)]
    with pytest.raises(ValueError, match=r"in \[0,1\]"):
        map_pose_frame(image_lm, world_lm, frame_index=0, timestamp_s=0.0, visibility_threshold=1.5)
    with pytest.raises(ValueError, match=r"in \[0,1\]"):
        map_pose_frame(image_lm, world_lm, frame_index=0, timestamp_s=0.0, visibility_threshold=-0.1)
    with pytest.raises(ValueError, match=r"in \[0,1\]"):
        map_pose_frame(image_lm, world_lm, frame_index=0, timestamp_s=0.0, visibility_threshold=True)
    # Valid threshold as int
    frame = map_pose_frame(image_lm, world_lm, frame_index=0, timestamp_s=0.0, visibility_threshold=1)
    assert frame.joints["left_shoulder"].valid is False  # quality 0.8 < threshold 1


def test_true_anatomy_fixture():
    # Create asymmetric data
    image_lm = [SimpleNamespace(x=0.1, y=0.2, visibility=0.9, presence=0.8) for _ in range(33)]
    world_lm = [SimpleNamespace(x=1.0, y=2.0, z=3.0) for _ in range(33)]
    # Left hip at (0.3, 0.2), right hip at (0.1, 0.2)
    image_lm[JOINT_INDICES["left_hip"]].x = 0.3
    image_lm[JOINT_INDICES["right_hip"]].x = 0.1
    world_lm[JOINT_INDICES["left_hip"]].x = 1.1
    world_lm[JOINT_INDICES["right_hip"]].x = 0.9
    frame = map_pose_frame(image_lm, world_lm, frame_index=0, timestamp_s=0.0)
    pelvis = frame.joints["pelvis"]
    assert pelvis.xy == (0.2, 0.2)
    assert pelvis.xyz == (1.0, -2.0, -3.0)
    assert frame.joints["left_hip"].xyz == (1.1, -2.0, -3.0)
    assert frame.joints["right_hip"].xyz == (0.9, -2.0, -3.0)


def test_invalid_types_rejected():
    # Test bool, string, NaN, inf in coordinates and quality
    image_lm = [SimpleNamespace(
        x="0.1", y=0.2, visibility=True, presence=0.8
    ) for _ in range(33)]
    world_lm = [SimpleNamespace(x=1.0, y=float('nan'), z=3.0) for _ in range(33)]
    frame = map_pose_frame(image_lm, world_lm, frame_index=0, timestamp_s=0.0)
    joint = frame.joints["left_shoulder"]
    assert joint.xy is None
    assert joint.xyz is None
    assert joint.valid is False


def test_offimage_xy_not_clamped():
    image_lm = [SimpleNamespace(x=1.5, y=-0.5, visibility=0.9, presence=0.8) for _ in range(33)]
    world_lm = [SimpleNamespace(x=1.0, y=2.0, z=3.0) for _ in range(33)]
    frame = map_pose_frame(image_lm, world_lm, frame_index=0, timestamp_s=0.0)
    joint = frame.joints["left_shoulder"]
    assert joint.xy == (1.5, -0.5)
    assert joint.valid is True


def test_derived_midpoint_one_side_invalid():
    image_lm = [SimpleNamespace(x=0.1, y=0.2, visibility=0.9, presence=0.8) for _ in range(33)]
    world_lm = [SimpleNamespace(x=1.0, y=2.0, z=3.0) for _ in range(33)]
    # Invalidate left hip
    image_lm[JOINT_INDICES["left_hip"]].x = float('inf')
    frame = map_pose_frame(image_lm, world_lm, frame_index=0, timestamp_s=0.0)
    pelvis = frame.joints["pelvis"]
    assert pelvis.valid is False
    assert "derived_paired_midpoint_unavailable" in pelvis.quality_method


@pytest.mark.parametrize("threshold", [float("nan"), float("inf"), "0.6", False])
def test_nonfinite_or_non_numeric_threshold(threshold):
    with pytest.raises(ValueError):
        map_pose_frame([], [], frame_index=0, timestamp_s=0, visibility_threshold=threshold)


def test_no_detection_keeps_all_joints_missing():
    frame = map_pose_frame([], [], frame_index=100, timestamp_s=10)
    assert all(not joint.valid and joint.xy is None and joint.xyz is None
               for joint in frame.joints.values())
