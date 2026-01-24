using UnityEngine;
using UnityEngine.UI; // Required for UI elements

public class BioVisualizer : MonoBehaviour
{
    [Header("Connections")]
    public BioReceiver receiver; // Drag your BioManager here
    public RectTransform targetRect; // Drag your UI Image (Rectangle) here

    [Header("Calibration (Map Sensor to Pixels)")]
    // GSR: 12000 (Relaxed) -> 6000 (Stressed)
    // Pulse: 0 (No signal) -> 1024 (Max signal)
    public Vector2 gsrRange = new Vector2(6000, 12000); 
    public Vector2 pulseRange = new Vector2(300, 800);

    [Header("Visual sizing")]
    public float minWidth = 100f;
    public float maxWidth = 800f;
    public float minHeight = 100f;
    public float maxHeight = 600f;

    [Header("Smoothing")]
    public float smoothSpeed = 5f; // Higher = faster snapping, Lower = smoother
    private Vector2 currentSize;

    void Update()
    {
        if (receiver == null || targetRect == null) return;

        // 1. Get Raw Data
        float rawGSR = receiver.sensor_1;   // Width Controller
        float rawPulse = receiver.sensor_2; // Height Controller

        // 2. Map Data to Size
        // Mathf.InverseLerp converts range to 0.0 - 1.0
        float widthPercent = Mathf.InverseLerp(gsrRange.x, gsrRange.y, rawGSR);
        float heightPercent = Mathf.InverseLerp(pulseRange.x, pulseRange.y, rawPulse);

        // Calculate Target Dimensions
        // Note: For GSR, lower value usually means HIGHER stress. 
        // If you want Stress = Wide, do (1 - widthPercent)
        float targetW = Mathf.Lerp(minWidth, maxWidth, widthPercent);
        float targetH = Mathf.Lerp(minHeight, maxHeight, heightPercent);

        // 3. Smooth the Movement (Linear Interpolation)
        // This prevents the box from jittering like crazy due to sensor noise
        Vector2 targetSize = new Vector2(targetW, targetH);
        currentSize = Vector2.Lerp(currentSize, targetSize, Time.deltaTime * smoothSpeed);

        // 4. Apply to UI
        targetRect.sizeDelta = currentSize;
    }
}