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
    [SerializeField] Transform rightHand;

    // UDP Objects
    private UdpClient udpClient;
    private IPEndPoint remoteEndPoint;

    void Start()
    {
        // Initialize UDP Client once
        udpClient = new UdpClient();
        remoteEndPoint = new IPEndPoint(IPAddress.Parse(ipAddress), port);

        Debug.Log($"UDP Sender started. Target: {ipAddress}:{port}");
    }

    void Update()
    {
        // 1. Get positions
        Vector3 myPos = transform.position;
        Vector3 rightPos = rightHand.position;

        // 2. Flatten the Y-axis (height) to ignore vertical difference
        myPos.y = 0;
        rightPos.y = 0;

        // 3. Calculate Distance
        // We no longer need Mathf.Min because there is only one hand to check.
        float currentDistance = Vector3.Distance(myPos, rightPos);

        Debug.Log($"Distance to Right Hand: {currentDistance:F2}");

        // 4. Send raw data over UDP
        SendString(currentDistance.ToString("F2"));
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

    // Clean up socket on exit
    private void OnApplicationQuit()
    {
        if (udpClient != null)
        {
            udpClient.Close();
            udpClient = null;
        }
    }
}