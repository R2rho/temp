from enum import IntFlag

class A3200AxisStatus(IntFlag):
    AXISSTATUS_Homed = 1
    AXISSTATUS_Profiling = 1 << 1
    AXISSTATUS_WaitDone = 1 << 2
    AXISSTATUS_CommandValid = 1 << 3
    AXISSTATUS_Homing = 1 << 4
    AXISSTATUS_Enabling = 1 << 5
    AXISSTATUS_JogGenerating = 1 << 7
    AXISSTATUS_Jogging = 1 << 8
    AXISSTATUS_DrivePending = 1 << 9
    AXISSTATUS_DriveAbortPending = 1 << 10
    AXISSTATUS_TrajectoryFiltering = 1 << 11
    AXISSTATUS_IFOVEnabled = 1 << 12
    AXISSTATUS_NotVirtual = 1 << 13
    AXISSTATUS_CalibrationEnabled1D = 1 << 14
    AXISSTATUS_CalibrationEnabled2D = 1 << 15
    AXISSTATUS_MasterSlaveControl = 1 << 16
    AXISSTATUS_JoystickControl = 1 << 17
    AXISSTATUS_BacklashActive = 1 << 18
    AXISSTATUS_GainMappingEnabled = 1 << 19
    AXISSTATUS_Stability0 = 1 << 20
    AXISSTATUS_MotionBlocked = 1 << 21
    AXISSTATUS_MoveDone = 1 << 22
    AXISSTATUS_MotionClamped = 1 << 23
    AXISSTATUS_GantryAligned = 1 << 24
    AXISSTATUS_GantryRealigning = 1 << 25
    AXISSTATUS_Stability1 = 1 << 26
    AXISSTATUS_ThermoCompEnabled = 1 << 27
