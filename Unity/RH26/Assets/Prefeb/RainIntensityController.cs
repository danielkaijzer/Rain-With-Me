using UnityEngine;

public class RainIntensityController : MonoBehaviour
{
    [Header("Target Particles")]
    public ParticleSystem rainSystem;

    [Header("Intensity Control")]
    [Range(0f, 1f)]
    public float rainIntensity = 0.5f;

    [Header("Max Limits")]
    public float maxEmission = 500f;

    // We remove 'maxSpeed' because rain shouldn't get 10x faster

    void Update()
    {
        if (rainSystem == null) return;

        // 1. Change Amount (This is the density/heaviness)
        var emission = rainSystem.emission;
        emission.rateOverTime = rainIntensity * maxEmission;

        // 2. Change Gravity slightly (Heavy rain falls a bit straighter/harder)
        var main = rainSystem.main;
        // Smaller range (1 to 3) prevents it from looking like lasers
        main.gravityModifier = Mathf.Lerp(1f, 3f, rainIntensity);

        // OPTIONAL: Make drops slightly larger when heavy
        // main.startSize = Mathf.Lerp(0.1f, 0.2f, rainIntensity);
    }
}