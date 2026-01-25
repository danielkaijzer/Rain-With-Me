using UnityEngine;
using System.Collections;

public class UIManager : MonoBehaviour
{
    public GameObject introPanel;
    public GameObject instructionsPanel;
    public AudioSource audioSource;
    public AudioClip startSound;

    private CanvasGroup canvasGroup;

    void Start()
    {
        introPanel.SetActive(true);
        instructionsPanel.SetActive(false);
        Debug.Log("UI Manager Initialized. Intro Panel is Active.");
    }

    public void OnStartButtonPressed()
    {
        Debug.Log("Button Clicked!");

        if (audioSource && startSound)
        {
            audioSource.PlayOneShot(startSound);
            Debug.Log("Playing Sound.");
        }

        introPanel.SetActive(false);
        instructionsPanel.SetActive(true);
        Debug.Log("Intro Panel OFF, Instructions Panel ON.");

        canvasGroup = instructionsPanel.GetComponent<CanvasGroup>();
        if (canvasGroup == null)
        {
            canvasGroup = instructionsPanel.AddComponent<CanvasGroup>();
        }
        
        canvasGroup.alpha = 1f;

        StopAllCoroutines();
        StartCoroutine(HandleInstructionsSequence());
    }

    IEnumerator HandleInstructionsSequence()
    {
        Debug.Log("Starting 4-second timer...");
        yield return new WaitForSeconds(4f);

        Debug.Log("Starting Fade Out...");
        float counter = 0;
        while (counter < 1.5f)
        {
            counter += Time.deltaTime;
            canvasGroup.alpha = Mathf.Lerp(1, 0, counter / 1.5f);
            yield return null;
        }

        instructionsPanel.SetActive(false);
        Debug.Log("Sequence Complete. Instructions Panel Hidden.");
    }
}