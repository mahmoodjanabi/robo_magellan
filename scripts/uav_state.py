#!/usr/bin/env python
#
# UAV State Model:
# Encapsulates UAV state and abstracts communication
# States:
# - Setpoint pose
# - local_position
# - MAV mode
# - arm

# import ROS libraries
import rospy
import mavros
from mavros.utils import *
from mavros import setpoint as SP
import mavros_msgs.msg
import mavros_msgs.srv

#
import time
from datetime import datetime
import enum

class AutoNumber(enum.Enum):
    def __new__(cls):
        value = len(cls.__members__) + 1
        obj = object.__new__(cls)
        obj._value_ = value
        return obj


class MODE(AutoNumber):
    MANUAL = ()
    RTL = ()
    
class ARM(AutoNumber):
    ARMED = ()
    DISARMED = ()

#
class _coord:
	def __init__(self):
		self.x = 0
		self.y = 0
		self.z = 0

#
class UAV_State:
    def __init__(self):
        self.current_pose = _coord()
        self.setpoint_pose = _coord()
        self.mode = "None"
        self.arm = "None"
        self.guided = "None"
        self.timestamp = float(datetime.utcnow().strftime('%S.%f'))
        self.connection_delay = 0.0
        mavros.set_namespace("/mavros")

        # Subscribers
        self.local_position_sub = rospy.Subscriber(mavros.get_topic('local_position', 'pose'), 
            SP.PoseStamped, self.__local_position_cb)
        self.setpoint_local_sub = rospy.Subscriber(mavros.get_topic('setpoint_raw', 'target_local'), 
            mavros_msgs.msg.PositionTarget, self.__setpoint_position_cb)
        self.state_sub = rospy.Subscriber(mavros.get_topic('state'),
            mavros_msgs.msg.State, self.__state_cb)
        pass

    def __local_position_cb(self, topic):
        self.current_pose.x = topic.pose.position.x
        self.current_pose.y = topic.pose.position.y
        self.current_pose.z = topic.pose.position.z

    def __setpoint_position_cb(self, topic):
        self.setpoint_pose.x = topic.position.x
        self.setpoint_pose.y = topic.position.y
        self.setpoint_pose.z = topic.position.z

    def __state_cb(self, topic):
        self.__calculate_delay()
        self.mode = topic.mode
        self.guided = topic.guided
        self.arm = topic.armed

    def __calculate_delay(self):
        tmp = float(datetime.utcnow().strftime('%S.%f'))
        if tmp<self.timestamp:
            # over a minute
            self.connection_delay = 60.0 - self.timestamp + tmp
        else:
            self.connection_delay = tmp - self.timestamp
        self.timestamp = tmp

    ####
    def get_mode(self):
        return self.mode

    def set_mode(self, new_mode):
        rospy.wait_for_service('/mavros/set_mode')
        try:
            flightModeService = rospy.ServiceProxy('/mavros/set_mode', mavros_msgs.srv.SetMode)
            isModeChanged = flightModeService(custom_mode=new_mode) 
        except rospy.ServiceException, e:
            rospy.loginfo("Service set_mode call failed: %s. Mode %s could not be set. Check that GPS is enabled.",e,new_mode)

    ####
    def get_arm(self):
        return self.arm

    def set_arm(self, new_arm):
        rospy.wait_for_service('/mavros/cmd/arming')
        try:
            armService = rospy.ServiceProxy('/mavros/cmd/arming', mavros_msgs.srv.CommandBool)
            armService(new_arm)
        except rospy.ServiceException, e:
            rospy.loginfo("Service arm call failed: %s. Attempted to set %s",e,new_arm)

    ####
    def get_current_pose(self):
        return self.current_pose

    def get_setpoint_pose(self):
        return self.setpoint_pose

    def get_guided(self):
        return self.guided

    def get_delay(self):
        return self.connection_delay
