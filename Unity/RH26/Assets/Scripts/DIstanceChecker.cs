using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using System.Net;
using System.Net.Sockets;
using System.Text;

public class DistanceChecker : MonoBehaviour
{
    [Header("Settings")]
    [SerializeField] float distanceThreshold = 10;

    [Header("UDP Settings")]
    [SerializeField] string ipAddress = "127.0.0.1"; // Localhost
    [SerializeField] int port = 5010;

    [Header("References")]
    [SerializeField] Transform leftHand;
    [SerializeField] Transform rightHand;

    // UDP Objects
    private UdpClient udpClient;
    private IPEndPoint remoteEndPoint;

    void Start()
    {
        // Initialize UDP Client once on Start to save performance
        udpClient = new UdpClient();
        remoteEndPoint = new IPEndPoint(IPAddress.Parse(ipAddress), port);

        Debug.Log($"UDP Sender started. Target: {ipAddress}:{port}");
    }

    void Update()
    {
        // 1. Get positions
        Vector3 myPos = transform.position;
        Vector3 leftPos = leftHand.position;
        Vector3 rightPos = rightHand.position;

        // 2. Flatten the Y-axis (height) to ignore it
        // We act as if everything is on the floor (y=0)
        myPos.y = 0;
        leftPos.y = 0;
        rightPos.y = 0;

        // 3. Calculate Distances using the flattened vectors
        float leftDist = Vector3.Distance(myPos, leftPos);
        float rightDist = Vector3.Distance(myPos, rightPos);

        Debug.Log($"Right: {rightDist} | Left: {leftDist}");

        // 4. Format the message
        // Format: "Hand:Distance"
        string messageLeft = $"Left:{leftDist:F2}";
        string messageRight = $"Right:{rightDist:F2}";

        // 5. Send Data over UDP
        SendString(messageLeft);
        SendString(messageRight);

        // 6. Logic Check (The "Vicinity" check)
        if (leftDist < distanceThreshold || rightDist < distanceThreshold)
        {
            SendString("STATUS:IN_VICINITY");
        }
    }

    // Helper method to encode and send data
    private void SendString(string message)
    {
        try
        {
            byte[] data = Encoding.UTF8.GetBytes(message);
            udpClient.Send(data, data.Length, remoteEndPoint);
        }
        catch (System.Exception e)
        {
            Debug.LogError($"UDP Send Error: {e.Message}");
        }
    }

    // IMPORTANT: Close the socket when the game stops or the script is destroyed
    private void OnApplicationQuit()
    {
        if (udpClient != null)
        {
            udpClient.Close();
            udpClient = null;
        }
    }
}