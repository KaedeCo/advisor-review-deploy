import { Link } from 'react-router-dom'
import { Button } from 'tdesign-react'

/**
 * 免责声明页面
 */
export default function DisclaimerPage() {
  return (
    <div className="page-container" style={{ maxWidth: '800px' }}>
      <div style={{ marginBottom: '28px' }}>
        <h2 style={{
          margin: 0, fontSize: '24px', fontWeight: 700,
          background: 'linear-gradient(135deg, #00D4FF, #B088F9)',
          WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
        }}>
          DISCLAIMER
        </h2>
        <p style={{ marginTop: '6px', color: 'var(--text-muted)', fontSize: '13px' }}>
          Legal Notice &amp; Terms of Use
        </p>
      </div>

      <div className="glass-card" style={{ padding: '32px 40px', lineHeight: 1.9, fontSize: '14px' }}>
        <h3 style={{ color: '#00D4FF', fontSize: '16px', marginBottom: '16px' }}>
          1. Information Source
        </h3>
        <p style={{ color: 'var(--text-secondary)', marginBottom: '24px' }}>
          This platform serves solely as an information aggregation and retrieval tool.
          All evaluation information is sourced from publicly available channels on the internet,
          including but not limited to GradChoice, PI Review, daoshipingjia.net, eeban.com,
          muchong.com, bbs.kaoyan.com, LetPub, and GitHub open datasets.
          This platform does not guarantee the authenticity, accuracy, or completeness of any information.
        </p>

        <h3 style={{ color: '#00D4FF', fontSize: '16px', marginBottom: '16px' }}>
          2. User-Generated Content
        </h3>
        <p style={{ color: 'var(--text-secondary)', marginBottom: '24px' }}>
          User reviews displayed on this platform represent the personal opinions of the reviewers
          and are not affiliated with this platform. Anyone may submit evaluations; readers should
          independently judge their credibility. This platform respects the reputation and privacy
          rights of every advisor.
        </p>

        <h3 style={{ color: '#00D4FF', fontSize: '16px', marginBottom: '16px' }}>
          3. Request Removal or Correction
        </h3>
        <p style={{ color: 'var(--text-secondary)', marginBottom: '24px' }}>
          If you discover inappropriate content, please apply for removal or correction.
          Contact the platform administrator to process your request.
          We are committed to handling all legitimate requests promptly.
        </p>

        <h3 style={{ color: '#00D4FF', fontSize: '16px', marginBottom: '16px' }}>
          4. Academic Purpose Only
        </h3>
        <p style={{ color: 'var(--text-secondary)', marginBottom: '24px' }}>
          This platform is intended for academic research and educational purposes only.
          It does not constitute any application or school selection advice.
          Users should make their own decisions based on comprehensive research.
        </p>

        <h3 style={{ color: '#00D4FF', fontSize: '16px', marginBottom: '16px' }}>
          5. Legal Compliance
        </h3>
        <p style={{ color: 'var(--text-secondary)', marginBottom: '24px' }}>
          This platform complies with the Cybersecurity Law of the People's Republic of China,
          the Data Security Law, the Personal Information Protection Law, and other relevant
          laws and regulations. All data collection follows the principles of legitimacy,
          necessity, and minimization.
        </p>

        <h3 style={{ color: '#00D4FF', fontSize: '16px', marginBottom: '16px' }}>
          6. Prohibited Uses
        </h3>
        <div style={{ color: 'var(--text-secondary)', marginBottom: '24px' }}>
          <p style={{ marginBottom: '8px' }}>The following actions are strictly prohibited:</p>
          <p style={{ marginLeft: '16px' }}>- Commercial sale of collected data</p>
          <p style={{ marginLeft: '16px' }}>- Bypassing paywalls to access paid content</p>
          <p style={{ marginLeft: '16px' }}>- Large-scale concurrent requests causing server pressure</p>
          <p style={{ marginLeft: '16px' }}>- Impersonating real persons or forging identities</p>
          <p style={{ marginLeft: '16px' }}>- Republishing copyrighted content in full</p>
          <p style={{ marginLeft: '16px' }}>- Using data for extortion or malicious defamation</p>
        </div>

        <h3 style={{ color: '#00D4FF', fontSize: '16px', marginBottom: '16px' }}>
          7. Limitation of Liability
        </h3>
        <p style={{ color: 'var(--text-secondary)', marginBottom: '24px' }}>
          This platform is not liable for any direct or indirect losses arising from the use of
          this service. Users assume full responsibility for their actions based on the information
          provided herein.
        </p>

        <div style={{
          marginTop: '32px', paddingTop: '20px',
          borderTop: '1px solid var(--border-color)',
          fontSize: '12px', color: 'var(--text-muted)',
        }}>
          <p>Last updated: June 17, 2026</p>
          <p>By using this platform, you agree to all terms and conditions stated above.</p>
        </div>
      </div>

      <div style={{ textAlign: 'center', marginTop: '24px' }}>
        <Link to="/">
          <Button variant="outline">Back to Home</Button>
        </Link>
      </div>
    </div>
  )
}
