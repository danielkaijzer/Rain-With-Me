using UnityEngine;

public class RainIntensityController : MonoBehaviour
{
    [Header("Connections")]
    public ParticleSystem rainSystem;
    public BioReceiver bioDataReceiver;

    [Header("Data Mapping")]
    // If your python sends 0.0-1.0, you can leave these as 0 and 1.
    public float inputMin = 0;
    public float inputMax = 1;

    [Header("Debug")]
    [Range(0f, 1f)]
    public float currentIntensity;

    [Header("Max Limits")]
    public float maxEmission = 1000f;
    public float maxSpeed = 20f;

    void Update()
    {
        if (rainSystem == null || bioDataReceiver == null) return;

        // 1. Get the final_arousal value
        float rawValue = bioDataReceiver.finalArousal;
        Debug.Log("Cur rain value:" + rawValue);

        // 2. Normalize (Ensure it stays 0.0 - 1.0)
        currentIntensity = Mathf.InverseLerp(inputMin, inputMax, rawValue);

        // 3. Apply to Rain Emission
        var emission = rainSystem.emission;
        emission.rateOverTime = currentIntensity * maxEmission;
    }
}