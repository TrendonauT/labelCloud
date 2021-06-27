"""
A module for aligning point clouds with the floor. The user has to span a triangle with
three points on the plane that serves as the ground. Then the old point cloud will be
saved up and the aligned current will overwrite the old.
"""
from typing import Union, TYPE_CHECKING

import numpy as np

import utils.oglhelper as ogl
from .pcd_manager import PointCloudManger

if TYPE_CHECKING:
    from view.gui import GUI


class AlignMode:
    def __init__(self, pcd_manager: PointCloudManger):
        self.pcd_manager = pcd_manager
        self.view: Union[GUI, None] = None
        self.activated = False
        self.point_color = (1, 1, 0, 1)
        self.area_color = (1, 1, 0, 0.6)
        self.plane1 = None
        self.plane2 = None
        self.plane3 = None

        self.tmp_p2 = None
        self.tmp_p3 = None

    def set_view(self, view: "GUI"):
        self.view = view
        self.view.glWidget.align_mode = self

    def is_active(self):
        return self.activated

    def change_activation(self, force=None):
        if force is not None:
            self.activated = force
        elif self.activated:
            self.activated = False
            self.reset()
        else:
            self.activated = True

        if self.activated:
            self.view.update_status(
                "Select three points on the plane that should be the floor.",
                "alignment",
            )
        self.view.action_alignpcd.setChecked(self.activated)
        self.view.activate_draw_modes(
            not self.activated
        )  # Prevent bbox drawing while aligning
        print("Alignmode was changed to %s!" % self.activated)

    def reset(self, points_only: bool = False):
        self.plane1, self.plane2, self.plane3 = (None, None, None)
        self.tmp_p2, self.tmp_p3 = (None, None)
        if not points_only:
            self.change_activation(force=False)

    def register_point(self, new_point):
        if self.plane1 is None:
            self.plane1 = new_point
        elif not self.plane2:
            self.plane2 = new_point
            self.view.update_status(
                "The triangle area should be part over and part under the floor points."
            )
        elif not self.plane3:
            self.plane3 = new_point
            self.calculate_angles()
        else:
            print("Cannot register point.")

    def register_tmp_point(self, new_tmp_point):
        if self.plane1 and (not self.plane2):
            self.tmp_p2 = new_tmp_point
        elif self.plane2 and (not self.plane3):
            self.tmp_p3 = new_tmp_point

    def draw_preview(self):
        if not self.plane3:
            if self.plane1:
                ogl.draw_points([self.plane1], color=self.point_color)

            if self.plane1 and (self.plane2 or self.tmp_p2):
                if self.plane2:
                    self.tmp_p2 = self.plane2
                ogl.draw_points([self.tmp_p2], color=self.point_color)
                ogl.draw_lines([self.plane1, self.tmp_p2], color=self.point_color)

            if self.plane1 and self.plane2 and (self.tmp_p3 or self.plane3):
                if self.plane3:
                    self.tmp_p3 = self.plane3

                ogl.draw_points(
                    [self.plane1, self.plane2, self.tmp_p3], color=self.point_color
                )
                ogl.draw_triangles(
                    [self.plane1, self.plane2, self.tmp_p3], color=self.area_color
                )

        elif self.plane1 and self.plane2 and self.plane3:

            ogl.draw_points(
                [self.plane1, self.plane2, self.plane3], color=self.point_color
            )
            ogl.draw_triangles(
                [self.plane1, self.plane2, self.plane3], color=self.area_color
            )

    def calculate_angles(self):
        # Calculate plane normal with self.plane1 as origin
        plane_normal = np.cross(
            np.subtract(self.plane2, self.plane1), np.subtract(self.plane3, self.plane1)
        )
        pn_normalized = plane_normal / np.linalg.norm(plane_normal)  # normalize normal
        z_axis = np.array([0, 0, 1])

        # Calculate axis-angle-rotation
        rotation_angle = np.arccos(np.dot(pn_normalized, z_axis))
        rotation_axis = np.cross(pn_normalized, z_axis) / np.linalg.norm(
            np.cross(pn_normalized, z_axis)
        )
        print(
            f"Alignment rotation: {round(rotation_angle, 2)} "
            f"around {np.round(rotation_axis, 2)}"
        )

        # Initiate point cloud rotation
        self.pcd_manager.rotate_pointcloud(rotation_axis, rotation_angle, self.plane1)

        self.view.update_status(
            "Aligned point cloud with the selected floor.", "navigation"
        )
        self.change_activation(force=False)
        self.reset()
