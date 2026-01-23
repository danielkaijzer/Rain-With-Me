using RayNeo;
using RayNeo.API;
using System;
using UnityEngine;

public class SlamDemoCtrl : MonoBehaviour
{
   
    // Start is called before the first frame update
    void Start()
    {
        Algorithm.EnableSlamHeadTracker();
    

        HeadTrackedPoseDriver.OnPostUpdate += OnPostUpdate;
    }

    private void OnPostUpdate(Pose pose)
    {
        Debug.Log($"[SlamDemoCtrl] OnPostUpdate() position = {pose.position}, rotation = {pose.rotation}");
    }

    private void OnDestroy()
    {
        HeadTrackedPoseDriver.OnPostUpdate -= OnPostUpdate;

        Algorithm.DisableSlamHeadTracker();
    }
    
    // Update is called once per frame
    void Update()
    {

    }
}
