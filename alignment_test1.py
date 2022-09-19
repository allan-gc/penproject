## License: Apache 2.0. See LICENSE file in root directory.
## Copyright(c) 2017 Intel Corporation. All Rights Reserved.

#####################################################
##              Align Depth to Color               ##
#####################################################

# First import the library
import pyrealsense2 as rs
# Import Numpy for easy array manipulation
import numpy as np
# Import OpenCV for easy image rendering
import cv2
from interbotix_xs_modules.xs_robot.arm import InterbotixManipulatorXS
import math
import modern_robotics as mr
# The robot object is what you use to control the robot
robot = InterbotixManipulatorXS("px100", "arm", "gripper")
mode = 'c'
robot.gripper.set_pressure(1.0)


#calibration of Prx,Pry,Prz (pen wrt robot)
prx,pry,prz=[0.248575, 0.0, 0.1931]

#cali of Pcx, Pcy, and Pcd (pen wrt camera)

pcx,pcy,pcd=[0.039599787443876266, -0.11097724735736847, 0.33800002932548523]


Ocy=pry+pcd
Ocx=prx+pcx
Ocz=prz+pcy



# Create a pipeline
pipeline = rs.pipeline()


# Create a config and configure the pipeline to stream
#  different resolutions of color and depth streams
config = rs.config()

# Get device product line for setting a supporting resolution
pipeline_wrapper = rs.pipeline_wrapper(pipeline)
pipeline_profile = config.resolve(pipeline_wrapper)
device = pipeline_profile.get_device()
device_product_line = str(device.get_info(rs.camera_info.product_line))

found_rgb = False
for s in device.sensors:
    if s.get_info(rs.camera_info.name) == 'RGB Camera':
        found_rgb = True
        break
if not found_rgb:
    print("The demo requires Depth camera with Color sensor")
    exit(0)

config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)

if device_product_line == 'L500':
    config.enable_stream(rs.stream.color, 960, 540, rs.format.bgr8, 30)
else:
    config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)

# Start streaming
profile = pipeline.start(config)
prfl = profile.get_stream(rs.stream.color)
intr = prfl.as_video_stream_profile().get_intrinsics()

# Getting the depth sensor's depth scale (see rs-align example for explanation)
depth_sensor = profile.get_device().first_depth_sensor()
depth_scale = depth_sensor.get_depth_scale()
print("Depth Scale is: " , depth_scale)

# We will be removing the background of objects more than
#  clipping_distance_in_meters meters away
clipping_distance_in_meters = 0.7 #1 meter
clipping_distance = clipping_distance_in_meters / depth_scale

# Create an align object
# rs.align allows us to perform alignment of depth frames to others frames
# The "align_to" is the stream type to which we plan to align depth frames.
align_to = rs.stream.color
align = rs.align(align_to)

# Streaming loop
try:
    while True:
        # Get frameset of color and depth
        frames = pipeline.wait_for_frames()
        # frames.get_depth_frame() is a 640x360 depth image
        
        

        # Align the depth frame to color frame
        aligned_frames = align.process(frames)

        # Get aligned frames
        aligned_depth_frame = aligned_frames.get_depth_frame() # aligned_depth_frame is a 640x480 depth image
        dpt = aligned_depth_frame.as_depth_frame()
        
        
        color_frame = aligned_frames.get_color_frame()

        # Validate that both frames are valid
        if not aligned_depth_frame or not color_frame:
            continue

        depth_image = np.asanyarray(aligned_depth_frame.get_data())
        color_image = np.asanyarray(color_frame.get_data())

        hsv = cv2.cvtColor(color_image, cv2.COLOR_BGR2HSV)
        #lower_purp = np.array([57,144,90])
        #upper_purp = np.array([150,255,255])
        #lower_purp = np.array([91,132,99])
        #upper_purp = np.array([134,255,255])
        lower_purp = np.array([115,100,30])
        upper_purp = np.array([150,255,255])
       
        mask = cv2.inRange(hsv, lower_purp, upper_purp)
        res = cv2.bitwise_and(hsv,hsv, mask= mask)
       


        # Remove background - Set pixels further than clipping_distance to grey
        #grey_color = 255
        #depth_image_3d = np.dstack((depth_image,depth_image,depth_image)) #depth image is 1 channel, color is 3 channels
        #bg_removed = np.where((depth_image_3d > clipping_distance) | (depth_image_3d <= 0), grey_color, color_image)

        #hsv = cv2.cvtColor(bg_removed, cv2.COLOR_BGR2HSV)
        #lower_purp = np.array([107,114,107])
        #upper_purp = np.array([147,255,255])
        #lower_purp = np.array([91,132,99])
        #upper_purp = np.array([134,255,255])
       
  
        #mask = cv2.inRange(hsv, lower_purp, upper_purp)
        #res = cv2.bitwise_and(hsv,hsv, mask= mask)

        contours, hierarchy = cv2.findContours(mask, 1,2)
        cx=0
        cy=0
        if len(contours)!=0:
            moment_list=[]
            #print(f"first contour: {len(contours)}")
            for cnt in contours:
                M=cv2.moments(cnt)
                #print(f"area = {M['m00']}")
                moment_list.append(M['m00'])
                #if M['m00'] !=0:
                   #moment_list.append(M['m00'])

            #print(f"num moments: {len(moment_list)}")
            #print(f"moments: {(moment_list)}")
            max_area_index=moment_list.index(max(moment_list))
            #print(f"max area = {max(moment_list)}")
            #print(f"max area index = {max_area_index}")
            finalcnt=contours[max_area_index]
            #print(f"max area contour = {finalcnt}")
            finalmoment=cv2.moments(finalcnt)
            #print(f"area = {finalmoment['m00']}")
            if finalmoment['m00']!=0:
                 cx = int(finalmoment['m10']/finalmoment['m00'])
                 cy = int(finalmoment['m01']/finalmoment['m00'])
                 #print(f"centroid  = {cx,cy}")

     
    
        cv2.drawContours(color_image, contours, -1, (0,255,0), 3)
        cv2.circle(color_image, (cx,cy), radius=5, color=(0, 0, 255), thickness=-1)    
        pixel_distance_in_meters = dpt.get_distance(cx,cy)
        #print(f"depth(m) of centroid  = {pixel_distance_in_meters}")
        [x,y,z]=rs.rs2_deproject_pixel_to_point(intr, [cx, cy], (pixel_distance_in_meters))
        #[x,y,z]=[x*depth_scale,y*depth_scale,z]
        print(f"x,y,z of pen in m  = {[x,y,z]}")

        #Calculate rotation angle given pen's location
        
        
        rob_curr_angle=0
        if z<0.5 and z!=0:
            p2rx=Ocx-x
            p2ry=Ocy-z
            p2rz=Ocz-y
            rho = np.sqrt(p2rx**2 + p2ry**2)
            phi = np.arctan2(p2ry, p2rx)
            error=phi-rob_curr_angle
            rob_curr_angle=phi
            robot.arm.set_single_joint_position(joint_name='waist',position=error,moving_time=2.0)


            joints = robot.arm.get_joint_commands()
            T = mr.FKinSpace(robot.arm.robot_des.M, robot.arm.robot_des.Slist, joints)
            [R, p] = mr.TransToRp(T) # get the rotation matrix and the displacement


            error_ee_pen_x,error_ee_pen_y, error_ee_pen_z=p2rx-p[0], p2ry-p[1], p2rz-p[2]
            #robot.arm.set_single_joint_position(joint_name='wrist_angle',position=(-p2rz),moving_time=2.0)
            #robot.arm.set_single_joint_position(joint_name='shoulder',position=error_ee_pen_x,moving_time=2.0)
            #if error_ee_pen_x and error_ee_pen_z ==0:
                #robot.gripper.grasp()
            #robot.arm.set_single_joint_position(joint_name='elbow',position=error_ee_pen_z,moving_time=2.0)
            robot.arm.set_ee_cartesian_trajectory(x=error_ee_pen_x,y=0, z=error_ee_pen_z)

            print(f"x error = {[error_ee_pen_x]}")
            if error_ee_pen_x <abs(0.01) and error_ee_pen_x!=0:
                robot.gripper.grasp()
                cv2.destroyAllWindows()
                break
                
            
         
            
        
        # Render images:
        #   depth align to color on left
        #   depth on right
        depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_image, alpha=0.03), cv2.COLORMAP_JET)
        #images = np.hstack((bg_removed, depth_colormap))

        cv2.namedWindow('Align Example', cv2.WINDOW_NORMAL)
        #cv2.imshow('Align Example', color_image)
        #cv2.imshow( 'bg_removed', centroid)
        #cv2.imshow('Align Example', bg_removed)
        cv2.imshow('Align Example', color_image)

        key = cv2.waitKey(1)
        # Press esc or 'q' to close the image window
        if key & 0xFF == ord('q') or key == 27:
            cv2.destroyAllWindows()
            break
finally:
    pipeline.stop()
    robot.arm.go_to_home_pose()
    robot.gripper.release()



