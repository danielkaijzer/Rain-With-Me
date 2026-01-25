//using UnityEngine;
//using System.Collections.Generic;

//public class GardenManager : MonoBehaviour
//{
//    [Header("Dependencies")]
//    public RainIntensityController rainController;

//    [Header("Garden Settings")]
//    public List<Transform> flowers; // Drag all your flower objects here
//    public float growSpeed = 2.0f;  // How fast they grow/shrink
//    public float rainThreshold = 0.1f; // Flowers appear if rain is less than 10%

//    void Update()
//    {
//        if (rainController == null) return;

//        // Determine target scale: 
//        // If rain is low (< 0.1), target is 1 (Grow). 
//        // If rain is high, target is 0 (Shrink/Hide).
//        float targetScale = (rainController.rainIntensity <= rainThreshold) ? 1f : 0f;

//        // Loop through every flower in the list and animate it
//        foreach (Transform flower in flowers)
//        {
//            if (flower == null) continue;

//            // Smoothly move current scale towards target scale
//            float currentScale = flower.localScale.x; // Assuming uniform scale (x=y=z)
//            float newScale = Mathf.Lerp(currentScale, targetScale, Time.deltaTime * growSpeed);

//            flower.localScale = Vector3.one * newScale;
//        }
//    }
//}